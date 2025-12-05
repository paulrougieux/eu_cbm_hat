from accli import WKubeTask


cz_ie_it_reference = WKubeTask(
    name="cz_ie_it_reference",
    job_folder="./",
    docker_filename="Dockerfile_cz_ie_it",
    command="bash /app/run_cz_ie_it_on_iiasa_accelerator.sh",
    required_cores=1,
    required_ram=1024 * 1024 * 512,
    required_storage_local=1024 * 1024 * 1,
    required_storage_workflow=1024 * 1024,
    timeout=60 * 60,
    conf={"output_mappings": "/app/local_data/output:acc://out"},
)

zz_scenario = WKubeTask(
    name="zz_scenario",
    job_folder="./",
    docker_filename="Dockerfile_zz",
    command="bash /app/run_zz_test_data_on_iiasa_accelerator.sh",
    required_cores=1,
    required_ram=1024 * 1024 * 512,
    required_storage_local=1024 * 1024 * 1,
    required_storage_workflow=1024 * 1024,
    timeout=60 * 60,
        conf={
        "output_mappings": "/app/local_data/output:acc://out",
        "no_cache": True  # Disable cache to check it still works
    },
)

