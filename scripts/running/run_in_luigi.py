"""Run the model in the Luigi workflow orchestration tool

Run the model in Luigi:

    cd /home/paul/eu_cbm/eu_cbm_hat/scripts/running
    luigi --module run_in_luigi RunCBM --combo reference --country-iso2 LU --final-year 2047 --local-scheduler

To re-run an already executed task, simply delete the output file.

Open the model output for exploration in python:

    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners["LU"][-1]
    >>> runner.post_processor.sink

Display the luigi output file

    cat  ~/eu_cbm/eu_cbm_data/output/luigi/reference_LU_2047.txt

"""

from datetime import datetime
import luigi
from eu_cbm_hat.core.continent import continent
from eu_cbm_hat import eu_cbm_data_pathlib


class RunCBM(luigi.Task):
    """Run EU-CBM-HAT as a Luigi task"""
    combo = luigi.Parameter()
    country_iso2 = luigi.Parameter()
    final_year = luigi.IntParameter()

    def output(self):
        """Build the output path relative to eu_cbm_data"""
        output_dir = eu_cbm_data_pathlib / "output/luigi"
        output_file = output_dir / f"{self.combo}_{self.country_iso2}_{self.final_year}.txt"
        return luigi.LocalTarget(str(output_file))

    def run(self):
        """Run EU-CBM-HAT for the given country, scenario and final year

        Write the runner log file to the luigi output file."""
        runner = continent.combos[self.combo].runners[self.country_iso2][-1]
        runner.num_timesteps = self.final_year - runner.country.inventory_start_year
        runner.run(keep_in_ram=False, verbose=False, interrupt_on_error=False)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.output().open('w') as f:
            f.write(runner.paths.log.contents)
            msg = f"{now} Scenario combination '{self.combo}' model run completed "
            msg += f"for country '{self.country_iso2}' until {self.final_year}.\n"
            f.write(msg)

if __name__ == "__main__":
    luigi.run()
