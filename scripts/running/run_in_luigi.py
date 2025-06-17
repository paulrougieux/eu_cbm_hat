"""Run the model in the Luigi workflow orchestration tool

Run the model in Luigi:

    cd /home/paul/eu_cbm/eu_cbm_hat/scripts/running
    luigi --module run_in_luigi RunCBM --country-iso2 LU --final-year 2047 --local-scheduler

Open model output for exploration in python:



    >>> from eu_cbm_hat.core.continent import continent
    >>> runner = continent.combos['reference'].runners["LU"][-1]
    >>> runner.post_processor.sink

"""

import luigi
from eu_cbm_hat.core.continent import continent

class RunCBM(luigi.Task):
    country_iso2 = luigi.Parameter()
    final_year = luigi.IntParameter()

    def output(self):
        return luigi.LocalTarget(f"output/{self.country_iso2}_{self.final_year}.txt")

    def run(self):
        runner = continent.combos['reference'].runners[self.country_iso2][-1]
        runner.num_timesteps = self.final_year - runner.country.inventory_start_year
        runner.run(keep_in_ram=False, verbose=False, interrupt_on_error=False)
        with self.output().open('w') as f:
            f.write(f"Model run completed for country {self.country_iso2}\n")

if __name__ == "__main__":
    luigi.run()
