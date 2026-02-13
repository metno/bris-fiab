import os
import click
import earthkit.data as ekd
from anemoi.inference.config.run import RunConfiguration
from anemoi.inference.runners.default import DefaultRunner


@click.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    default="config.yaml",
    show_default=True,
    help="Inference configuration file",
)
def run(config: str):
    """Run inference based on a provided configuration file."""
    configuration = RunConfiguration.load(config)

    cache_policy = os.getenv("EARTHKIT_DATA_CACHE_POLICY", "user")
    ekd.config.set("cache-policy", cache_policy)

    runner = DefaultRunner(configuration)

    import torch

    if torch.cuda.is_available():
        print("Using CUDA")
        runner.device = "cuda"
    elif torch.backends.mps.is_available():
        print("Using MPS")
        runner.device = "mps"
    else:
        print("Using CPU")
        runner.device = "cpu"

    runner.execute()
