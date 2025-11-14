
Scripts in this directory run CBM on the IIASA Accelerator platform.

- IIASA accelerator https://accelerator.iiasa.ac.at/

    - EU CBM space https://accelerator.iiasa.ac.at/projects/eu-cbm/file-explorer


# Install the accelerator CLI client

Install a Python client for the IIASA accelerator

    pip install accli
    pip install --upgrade accli
    accli about

Login with Auth0 authentication. It will create a link to your web browser, where you
will be able to copy an authentication key, to be pasted back at the command line
prompt:

    accli login

## Documentation and code

Documentation and source code of the client:

- source code https://github.com/iiasa/accelerator_non-web_client

- python docs in a workshop presentation
  https://github.com/andrenakhavali/accelerator_workshop/blob/main/3_2_Routine_for_Python_script.md

- Auth0 Device Authorization Flow
  https://auth0.com/docs/get-started/authentication-and-authorization-flow/device-authorization-flow


# Run

see also

- ~/eu_cbm/eu_cbm_explore/projects/iiasa_cbm_run


Start a model run by dispatching a routine to the accelerator platform

    cd ~/eu_cbm/eu_cbm_hat/scripts/running/iiasa_accelerator
    accli login
    accli dispatch eu-cbm zz_scenario



