"""Base processor abstract class."""

from abc import ABC, abstractmethod

from glocaltext.models import ExecutionContext

__all__ = ["Processor"]


class Processor(ABC):
    """Abstract base class for all processors in the pipeline."""

    @abstractmethod
    def process(self, context: ExecutionContext) -> None:
        """
        Process the execution context.

        Args:
            context: The execution context to process.

        """
        raise NotImplementedError
