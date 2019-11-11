FROM lsstdesc/stack-sims:w_2019_42-sims_w_2019_42-v2

USER root
RUN mkdir -p /DC2 &&\
  chown lsst /DC2
USER lsst
RUN set +e &&\
  source scl_source enable devtoolset-8 &&\
  set -e &&\ 
  source /opt/lsst/software/stack/loadLSST.bash &&\
  setup lsst_sims -t sims_w_2019_42 &&\
  setup -t DC2production throughputs &&\
  setup -t DC2production sims_skybrightness_data &&\
  cd /DC2 &&\
  git clone https://github.com/LSSTDESC/imSim.git &&\
  git clone https://github.com/LSSTDESC/DESC_DC2_imSim_Workflow.git &&\
  setup -r imSim -j &&\
  cd imSim &&\
  git checkout v0.6.1 &&\
  scons &&\
  cd ../DESC_DC2_imSim_Workflow &&\
  git checkout Run2.2i-production-v1
ENTRYPOINT ["/DC2/DESC_DC2_imSim_Workflow/docker_run.sh"]
CMD ["echo You must specify a command to run inside the LSST ALCF container"]

