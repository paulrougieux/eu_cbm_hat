"""This app starts model runs of EU-CBM-HAT and displays the log files

Usage:

    cd ~/eu_cbm/eu_cbm_hat/scripts/running/app
    streamlit run eu_cbm_app.py

"""

from pathlib import Path
import os
import re
import streamlit as st
import subprocess
import threading
import time

from eu_cbm_hat import eu_cbm_data_pathlib
from eu_cbm_hat.core.continent import continent

# Initialize session state for process tracking
if "processes" not in st.session_state:
    st.session_state.processes = {}
if "process_status" not in st.session_state:
    st.session_state.process_status = {}

SCENARIO_COMBOS = sorted(continent.combos.keys())

COUNTRIES = [
    "AT",
    "BE",
    "BG",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
    "ZZ",
]


def slugify(text: str) -> str:
    """Convert scenario names to link anchors
    Convert to lowercase and replace _ and + with - to mimic streamlit's
    automated creation of link anchors based on markdown titles"""
    text = text.lower()
    return re.sub(r"[_+]", "-", text)


def generate_toc(scenarios):
    """Table of content with all scenario names"""
    st.sidebar.markdown("## Available Scenarios")
    for combo_name in scenarios:
        anchor_id = slugify(combo_name)
        st.sidebar.markdown(f"- [{combo_name}](#{anchor_id})")


def get_log_path(combo_name, country):
    """Generate a log file path based on scenario name and country"""
    return eu_cbm_data_pathlib / f"output/{combo_name}/{country}/0/logs/runner.log"


def get_combo_path(combo_name):
    """Generate a path to the scenario combo yaml file based on scenario name"""
    return eu_cbm_data_pathlib / f"combos/{combo_name}.yaml"


def log_indicates_done(log_path):
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                return "Done." in f.read()
        except Exception:
            pass
    return False


def check_process_status(combo_name, country):
    """Check if a process is done or still running"""
    process_key = f"{combo_name}_{country}"
    if log_indicates_done(get_log_path(combo_name, country)):
        return "completed"
    if process_key in st.session_state.processes:
        process = st.session_state.processes[process_key]
        if process.poll() is None:
            return "running"
        else:
            return "failed"
    return "not_started"


def run_scenario(combo_name, country):
    """Run a scenario in a separate process"""
    try:
        # Create unique key for country-specific processes
        process_key = f"{combo_name}_{country}"

        # Prepare the command
        cmd = f"""
        source ~/.bashrc
        conda activate susbiom_trade_env
        cd $HOME/eu_cbm/eu_cbm_hat/scripts/running/
        ipython run_scenario_combo.py -- --combo_name {combo_name} --last_year 2100 --countries {country}
        """

        # Start the process
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable="/bin/bash",
        )

        # Store process in session state
        st.session_state.processes[process_key] = process
        st.session_state.process_status[process_key] = "running"

        # Wait for completion in a separate thread
        def wait_for_completion():
            process.wait()
            if process.returncode == 0:
                st.session_state.process_status[process_key] = "completed"
            else:
                st.session_state.process_status[process_key] = "failed"

        thread = threading.Thread(target=wait_for_completion)
        thread.daemon = True
        thread.start()

        return True
    except Exception as e:
        st.session_state.process_status[f"{combo_name}_{country}"] = f"error: {str(e)}"
        return False


def stop_scenario(combo_name, country):
    """Stop a running scenario"""
    process_key = f"{combo_name}_{country}"
    try:
        if process_key in st.session_state.processes:
            process = st.session_state.processes[process_key]
            if process.poll() is None:  # Process is still running
                process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    process.wait()

                st.session_state.process_status[process_key] = "stopped"
                return True
        return False
    except Exception as e:
        st.session_state.process_status[process_key] = f"error stopping: {str(e)}"
        return False


def get_status_color(status):
    """Get color for status display"""
    colors = {
        "running": "🟡",
        "completed": "🟢",
        "failed": "🔴",
        "stopped": "🟠",
        "not_started": "⚪",
    }
    return colors.get(status, "⚪")


################
# Streamlit UI #
################
generate_toc(SCENARIO_COMBOS)
st.title("🌲 EU-CBM-HAT Scenarios 🌳")
st.markdown("See the status of EU-CBM-HAT simulation scenarios.")
st.markdown("Click on 'view combo' to view the scenario yaml file.")
st.markdown("Click on 'view log' to view a country's log file.")

# Auto-refresh every 5 seconds to update status
time.sleep(0.2)  # Small delay to prevent too frequent updates
# Note pip install streamlit-autorefresh could be used here but it introduces
# another dependency

# Create columns for better layout
col1, col2 = st.columns([3, 1])

with col1:
    for combo_name in SCENARIO_COMBOS:
        scenario_name = combo_name

        # Create container for each scenario
        with st.container():
            st.markdown(f"#### {scenario_name}")

            # combo file link
            combo_path = get_combo_path(combo_name)
            if os.path.exists(combo_path):
                if st.button(f"📖 View combo", key=f"combo_{combo_name}"):
                    try:
                        with open(combo_path, "r") as f:
                            combo_content = f.read()
                        st.text_area(
                            f"combo for {scenario_name}",
                            combo_content,
                            height=300,
                            key=f"combo_content_{combo_name}",
                        )
                    except Exception as e:
                        st.error(f"Could not read combo file: {e}")
            else:
                st.markdown("📄 combo (not found)")

            for country in COUNTRIES:
                # Get current status for this country
                current_status = check_process_status(combo_name, country)
                status_display = get_status_color(current_status)

                # Create button row
                if current_status == "running":
                    # Show stop button when running
                    if st.button(
                        f"⏹️ Stop {country}",
                        key=f"stop_{combo_name}_{country}",
                        help=f"Stop {scenario_name} for {country}",
                        type="secondary",
                    ):
                        with st.spinner(f"Stopping {scenario_name} for {country}..."):
                            success = stop_scenario(combo_name, country)
                            if success:
                                st.warning(f"Stopped {scenario_name} for {country}")
                            else:
                                st.error(
                                    f"Failed to stop {scenario_name} for {country}"
                                )
                else:
                    # Show run button when not running
                    if st.button(
                        f"▶️ Run {country}",
                        key=f"btn_{combo_name}_{country}",
                        disabled=False,
                        help=f"Start {scenario_name} for {country}",
                    ):
                        with st.spinner(f"Starting {scenario_name} for {country}..."):
                            success = run_scenario(combo_name, country)
                            if success:
                                st.success(f"Started {scenario_name} for {country}")
                            else:
                                st.error(
                                    f"Failed to start {scenario_name} for {country}"
                                )

                # Status display
                st.markdown(
                    f"{status_display} {current_status.replace('_', ' ').title()}"
                )

                # Log file link
                log_path = get_log_path(combo_name, country)
                if os.path.exists(log_path):
                    if st.button(f"📖 View Log", key=f"log_{combo_name}_{country}"):
                        try:
                            with open(log_path, "r") as f:
                                log_content = f.read()
                            st.text_area(
                                f"Log for {scenario_name} - {country}",
                                log_content,
                                height=300,
                                key=f"log_content_{combo_name}_{country}",
                            )
                        except Exception as e:
                            st.error(f"Could not read log file: {e}")
                else:
                    st.markdown("📄 Log (not yet created)")

            st.divider()

with col2:
    st.markdown("### Process Summary")

    # Summary of all processes for both countries
    all_statuses = []
    for combo in SCENARIO_COMBOS:
        for country in ["IT", "LU"]:
            all_statuses.append(check_process_status(combo, country))

    running_count = sum(1 for status in all_statuses if status == "running")
    completed_count = sum(1 for status in all_statuses if status == "completed")
    failed_count = sum(1 for status in all_statuses if status == "failed")
    stopped_count = sum(1 for status in all_statuses if status == "stopped")

    st.metric("🟡 Running", running_count)
    st.metric("🟢 Completed", completed_count)
    st.metric("🔴 Failed", failed_count)
    st.metric("🟠 Stopped", stopped_count)

    # Refresh button
    if st.button("🔄 Refresh Status"):
        st.rerun()

# Auto-refresh every 10 seconds
if running_count > 0:
    time.sleep(10)
    st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "**Note:** Scenarios run in parallel. Check log files for detailed progress information."
)
st.markdown(
    "**Environment:** `susbiom_trade_env` | **Target Countries:** IT, LU | **End Year:** 2100"
)
