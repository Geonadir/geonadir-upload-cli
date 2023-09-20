import concurrent.futures
import json
import logging
import os
from importlib.metadata import version

import click

from .parallel import process_thread
from .dataset import search_datasets, dataset_info

LEGAL_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"

logger = logging.getLogger(__name__)
env = os.environ.get("DEPLOYMENT_ENV", "prod")
log_level = logging.INFO
if env != "prod":
    log_level = logging.DEBUG
logging.basicConfig(level=log_level)


def print_version(ctx, param, value):
    # print(ctx.__dict__)
    # print(param.__dict__)
    # print(value)
    if not value or ctx.resilient_parsing:
        return
    click.echo(f'Version: {version("geonadir-upload-cli")}')
    ctx.exit()


@click.group()
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Package version.",
)
def cli():
    pass


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    show_default=True,
    help="Dry-run.",
)
@click.option(
    "--base-url", "-u",
    default="https://api.geonadir.com",
    show_default=True,
    type=str,
    required=False,
    help="Base url of geonadir api.",
)
@click.password_option(
    "--token", "-t",
    help="User token for authentication.",
)
@click.option(
    "--private/--public", "-p",
    default=False,
    show_default=True,
    type=bool,
    required=False,
    help="Whether dataset is private.",
)
@click.option(
    "--metadata", "-m",
    type=click.Path(exists=True),
    required=False,
    help="Metadata json file.",
)
@click.option(
    "--output-folder", "-o",
    is_flag=False,
    flag_value=os.getcwd(),
    type=click.Path(exists=True),
    required=False,
    help="Whether output csv is created. Generate output at the specified path. Default is false. If flagged without specifing output folder, default is the current path of your terminal.",
)
@click.option(
    "--item", "-i",
    type=(str, click.Path(exists=True)),
    required=True,
    multiple=True,
    help="The name of the dataset and the directory of images to be uploaded.",
)
@click.option(
    "--complete", "-c",
    default=False,
    show_default=True,
    type=bool,
    required=False,
    help="Whether post the uploading complete message to trigger the orthomosaic call.",
)
def upload_dataset(**kwargs):
    base_url = kwargs.get("base_url")
    token = kwargs.get("token")
    item = kwargs.get("item")
    private = kwargs.get("private")
    dry_run = kwargs.get("dry_run")
    metadata_json = kwargs.get("metadata")
    output_dir = kwargs.get("output_folder")
    complete = kwargs.get("complete")

    if dry_run:
        logger.info("---------------------dry run---------------------")
        logger.info(f"base_url: {base_url}")
        logger.info(f"token: {token}")
        logger.info(f"metadata: {metadata_json}")
        logger.info(f"private: {private}")
        logger.info(f"complete: {complete}")
        for i in item:
            logger.info("item:")
            dataset_name, image_location = i
            dataset_name = "".join(x for x in dataset_name.replace(" ", "_") if x in LEGAL_CHARS)
            if not dataset_name:
                logger.warning("No legal characters in dataset name. Named 'untitled' instead.")
                dataset_name = "untitled"
            logger.info(f"\tdataset name: {dataset_name}")
            logger.info(f"\timage location: {image_location}")
            if output_dir:
                logger.info(f"\toutput file: {os.path.join(output_dir, f'{dataset_name}.csv')}")
            else:
                logger.info("\tno output csv file")
        return

    logger.info(base_url)
    token = "Token " + token
    if metadata_json:
        with open(metadata_json) as f:
            metadata = json.load(f)
        logger.info(f"metadata: {metadata_json}")
    dataset_details = []
    for i in item:
        dataset_name, image_location = i
        dataset_name = "".join(x for x in dataset_name.replace(" ", "_") if x in LEGAL_CHARS)
        if not dataset_name:
            logger.warning("No legal characters in dataset name. Named 'untitled' instead.")
            dataset_name = "untitled"
        logger.info(f"Dataset name: {dataset_name}")
        logger.info(f"Images location: {image_location}")
        meta = None
        if metadata_json:
            meta = metadata.get(dataset_name, None)
            if meta:
                logger.info(f"Metadata specified for dataset {dataset_name} in {metadata_json}")

        dataset_details.append(
            (dataset_name, image_location, base_url, token, private, meta, complete)
        )
    if complete:
        logger.info("Orthomosaic will be triggered after uploading.")
    num_threads = len(dataset_details) if len(dataset_details) <= 5 else 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_thread, *params) for params in dataset_details]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
        if output_dir:
            for dataset_name, df in results:
                df.to_csv(f"{os.path.join(output_dir, dataset_name)}.csv", index=False)
                logger.info(f"output file: {os.path.join(output_dir, dataset_name)}.csv")
        else:
            logger.info("no output csv file")


@cli.command()
@click.option(
    "--base-url", "-u",
    default="https://api.geonadir.com",
    show_default=True,
    type=str,
    required=False,
    help="Base url of geonadir api.",
)
@click.argument('search-str')
def search_dataset(**kwargs):
    base_url = kwargs.get("base_url")
    search = kwargs.get("search_str")
    print(json.dumps(search_datasets(search, base_url), indent=4))


@cli.command()
@click.option(
    "--base-url", "-u",
    default="https://api.geonadir.com",
    show_default=True,
    type=str,
    required=False,
    help="Base url of geonadir api.",
)
@click.argument('project-id')
def get_dataset_info(**kwargs):
    base_url = kwargs.get("base_url")
    project_id = kwargs.get("project_id")
    print(json.dumps(dataset_info(project_id, base_url), indent=4))


if __name__ == "__main__":
    cli()
