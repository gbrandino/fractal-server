import logging
from pathlib import Path
from typing import Optional

from ..models import Dataset
from ..models import Project
from ..models.task import Task


async def auto_output_dataset(
    *,
    project: Project,
    input_dataset: Dataset,
    workflow: Task,
    overwrite_input: bool = False,
):
    """
    Determine the output dataset if it was not provided explicitly

    Only datasets containing exactly one path can be used as output.

    Returns
    -------
    output_dataset (Dataset):
        the output dataset
    """
    if overwrite_input and not input_dataset.read_only:
        input_paths = input_dataset.paths
        if len(input_paths) != 1:
            raise ValueError
        output_dataset = input_dataset
    else:
        raise NotImplementedError

    return output_dataset


def validate_workflow_compatibility(
    *,
    input_dataset: Dataset,
    workflow: Task,
    output_dataset: Optional[Dataset] = None,
):
    """
    Check compatibility of workflow and input / ouptut dataset
    """
    if (
        workflow.input_type != "Any"
        and workflow.input_type != input_dataset.type
    ):
        raise TypeError(
            f"Incompatible types `{workflow.input_type}` of workflow "
            f"`{workflow.name}` and `{input_dataset.type}` of dataset "
            f"`{input_dataset.name}`"
        )

    if not output_dataset:
        if input_dataset.read_only:
            raise ValueError("Input dataset is read-only")
        else:
            input_paths = input_dataset.paths
            if len(input_paths) != 1:
                # Only single input can be safely transformed in an output
                raise ValueError(
                    "Cannot determine output path: multiple input "
                    "paths to overwrite"
                )
            else:
                output_path = input_paths[0]
    else:
        output_path = output_dataset.paths
        if len(output_path) != 1:
            raise ValueError(
                "Cannot determine output path: Multiple paths in dataset."
            )
    return output_path


def set_job_logger(
    *,
    logger_name: str,
    log_file_path: Path,
    level: int = logging.warning,
    formatter: Optional[logging.Formatter] = None,
) -> logging.Logger:
    """
    Return a dedicated per-job logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel = level
    file_handler = logging.FileHandler(log_file_path, mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def close_job_logger(logger: logging.Logger) -> None:
    """
    Close all FileHandles of `logger`
    """
    for handle in logger.handlers:
        if isinstance(handle, logging.FileHandler):
            handle.close()
