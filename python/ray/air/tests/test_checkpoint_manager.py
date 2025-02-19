import pytest
from ray.air._internal.checkpoint_manager import (
    _CheckpointManager,
    CheckpointStorage,
    CheckpointConfig,
    _TrackedCheckpoint,
)


def test_unlimited_persistent_checkpoints():
    cpm = _CheckpointManager(checkpoint_strategy=CheckpointConfig(num_to_keep=None))

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint({"data": i}, storage_mode=CheckpointStorage.PERSISTENT)
        )

    assert len(cpm._top_persisted_checkpoints) == 10


def test_limited_persistent_checkpoints():
    cpm = _CheckpointManager(checkpoint_strategy=CheckpointConfig(num_to_keep=2))

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint({"data": i}, storage_mode=CheckpointStorage.PERSISTENT)
        )

    assert len(cpm._top_persisted_checkpoints) == 2


def test_no_persistent_checkpoints():
    # Remove argument validation in order to test `num_to_keep=0` in the common
    # AIR checkpoint manager
    # CheckpointConfig doesn't allow this since Tune + Train both use Tune's
    # checkpoint manager, which requires `num_to_keep >= 1`
    class _CheckpointConfig(CheckpointConfig):
        def __post_init__(self):
            pass

    cpm = _CheckpointManager(checkpoint_strategy=_CheckpointConfig(num_to_keep=0))

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint({"data": i}, storage_mode=CheckpointStorage.PERSISTENT)
        )

    assert len(cpm._top_persisted_checkpoints) == 0


def test_dont_persist_memory_checkpoints():
    cpm = _CheckpointManager(checkpoint_strategy=CheckpointConfig(num_to_keep=None))
    cpm._persist_memory_checkpoints = False

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint({"data": i}, storage_mode=CheckpointStorage.MEMORY)
        )

    assert len(cpm._top_persisted_checkpoints) == 0


def test_persist_memory_checkpoints():
    cpm = _CheckpointManager(checkpoint_strategy=CheckpointConfig(num_to_keep=None))
    cpm._persist_memory_checkpoints = True

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint({"data": i}, storage_mode=CheckpointStorage.MEMORY)
        )

    assert len(cpm._top_persisted_checkpoints) == 10


def test_keep_best_checkpoints():
    cpm = _CheckpointManager(
        checkpoint_strategy=CheckpointConfig(
            num_to_keep=2,
            checkpoint_score_attribute="metric",
            checkpoint_score_order="min",
        )
    )
    cpm._persist_memory_checkpoints = True

    for i in range(10):
        cpm.register_checkpoints(
            _TrackedCheckpoint(
                {"data": i},
                storage_mode=CheckpointStorage.MEMORY,
                metrics={"metric": i},
            )
        )

    # Sorted from worst (max) to best (min)
    assert [
        cp.tracked_checkpoint.metrics["metric"] for cp in cpm._top_persisted_checkpoints
    ] == [1, 0]


@pytest.mark.parametrize(
    "metrics",
    [
        {"nested": {"sub": {"attr": 5}}},
        {"nested": {"sub/attr": 5}},
        {"nested/sub": {"attr": 5}},
        {"nested/sub/attr": 5},
    ],
)
def test_nested_get_checkpoint_score(metrics):
    cpm = _CheckpointManager(
        checkpoint_strategy=CheckpointConfig(
            num_to_keep=2,
            checkpoint_score_attribute="nested/sub/attr",
            checkpoint_score_order="max",
        )
    )

    assert cpm._get_checkpoint_score(
        _TrackedCheckpoint(
            dir_or_data=None,
            metrics=metrics,
            storage_mode=CheckpointStorage.MEMORY,
        )
    ) == (True, 5.0, None), metrics


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
