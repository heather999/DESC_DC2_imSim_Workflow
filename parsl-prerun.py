import collections
import glob
import time
import pathlib
import json
import sys

import parsl
from parsl.app.app import bash_app

import logging

from functools import partial

logger = logging.getLogger("parsl.appworkflow")

parsl.set_stream_logger()
parsl.set_stream_logger(__name__)

logger.info("No-op log message to test log configuration")

# import configuration after setting parsl logging, because interesting
# construction happens during the configuration

import configuration

parsl.load(configuration.parsl_config)

# given a commandline, wrap it so that we'll invoke
# shifter appropriately (so that we don't need to
# hardcode shifter / singularity command lines all
# over the place.
def shifter_wrapper(img, cmd):
  wrapped_cmd = "shifter --entrypoint --image={} {}".format(img, cmd)
  return wrapped_cmd

@bash_app(executors=['submit-node'])
def validate_transfer(wrap, inst_cat_root: str, tarball_json: str):
    base = "/global/homes/d/descim/ALCF_1.2i/scripts/parsl-validate-transfer.py {} {}".format(inst_cat_root, tarball_json)
    c = wrap(base)
    logger.debug("validate_transfer command is: {}".format(c))
    return c   

@bash_app(executors=['submit-node'])
def generate_worklist(wrap, inst_cat_root: str, work_json: str, bundle_json: str):
    base = "/global/homes/d/descim/ALCF_1.2i/scripts/parsl-initial-worklist.py {} {} {}".format(inst_cat_root, work_json, bundle_json)
    c = wrap(base)
    logger.debug("generate_worklist command is: {}".format(c))
    return c
#    return "singularity exec -B {},{},/projects/LSSTADSP_DESC {} /projects/LSSTADSP_DESC/Run2.0i-parsl/ALCF_1.2i/scripts/parsl-initial-worklist.py {} {} {}".format(inst_cat_root, work_and_out_base, singularity_img_path, inst_cat_root, work_json, bundle_json)

@bash_app(executors=['submit-node'])
def generate_bundles(wrap, inst_cat_root: str, work_and_out_base, work_json: str, bundle_json: str, bundler_restart_path: str):
    c = wrap("/global/homes/d/descim/ALCF_1.2i/scripts/parsl-bundle.py {} {} {} {} {}".format(inst_cat_root, work_json, bundle_json, work_and_out_base + "/run/outputs/", bundler_restart_path))
    logger.debug("generate_bundles command is: {}".format(c))
    return c
    # return "singularity exec -B {},{},/projects/LSSTADSP_DESC {} /projects/LSSTADSP_DESC/Run2.0i-parsl/ALCF_1.2i/scripts/parsl-bundle.py {} {} {} {} {}".format(inst_cat_root, work_and_out_base, singularity_img_path, inst_cat_root, work_json, bundle_json, work_and_out_base + "/run/outputs/", bundler_restart_path)

@bash_app(executors=['submit-node'])
def cache_singularity_image(local_file, url):
    return "singularity build {} {}".format(local_file, url)

@bash_app(executors=['submit-node'])
def cache_shifter_image(image_tag):
    return "shifterimg -v pull {}".format(image_tag)

container_wrapper = partial(shifter_wrapper, configuration.singularity_img)

logger.info("caching container image")

# first pull a shifter/singularity image as necessary.
if (not configuration.fake) and configuration.singularity_download:
  if configuration.MACHINEMODE == "theta":
    singularity_future = cache_singularity_image(configuration.singularity_img, configuration.singularity_url)
    singularity_future.result()
  elif configuration.MACHINEMODE == "cori":
    shifter_future = cache_shifter_image(configuration.singularity_img)
    shifter_future.result()

# then, transfer all desired files via a tarball list.
if configuration.validate_transfer:
  logger.info("validating transfer")
  validate_future = validate_transfer(container_wrapper, configuration.inst_cat_root, configuration.tarball_list)
  validate_future.result()

# then generate a worklist given all desired files have been transferred.
if configuration.worklist_generate:
  logger.info("generating worklist")
  worklist_future = generate_worklist(container_wrapper, configuration.inst_cat_root, configuration.original_work_list, configuration.bundle_lists)
  worklist_future.result()

logger.info("generating bundles")

pathlib.Path(configuration.bundler_restart_path).mkdir(parents=True, exist_ok=True) 

# then make some bundles. This can all work on the log-in node.
bundle_future = generate_bundles(container_wrapper, configuration.inst_cat_root, configuration.work_and_out_path, configuration.original_work_list, configuration.bundle_lists, configuration.bundler_restart_path)

bundle_future.result()

logger.info("Loading bundles from {}".format(configuration.bundle_lists))

with open(configuration.bundle_lists) as fp:
  bundles = json.load(fp)
logger.info("Created {} bundles".format(len(bundles)))

logger.info("end of parsl-prerun")

