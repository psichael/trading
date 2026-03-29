import pytest
from mvs_harness.spf_compiler.graph_validator import validate_plan_graph
from mvs_harness.schemas.spf_plan_models import SpfTaskDocument, SpfTaskInput, SpfTaskOutput

@pytest.fixture
def valid_graph():
    """A fixture for a valid plan graph with no cycles or broken refs."""
    return {
        "epics": {
            "e1": {
                "tasks": {
                    "t1": SpfTaskDocument(
                        id="t1", title="Task 1", type="task", status="pending",
                        component_ids=["c1"], implements_contract_id="k1",
                        inputs=[], outputs=[SpfTaskOutput(id="i1", type="file", artifact_path="t1.out")], 
                        content="Task content."
                    ),
                    "t2": SpfTaskDocument(
                        id="t2", title="Task 2", type="task", status="pending",
                        component_ids=["c1"], implements_contract_id="k2",
                        inputs=[SpfTaskInput(id="i1", source_task_id="t1", description="")],
                        outputs=[],
                        content="Task content."
                    )
                }
            }
        }
    }

@pytest.fixture
def invalid_ref_graph(valid_graph):
    """A graph with a task that depends on a non-existent task."""
    valid_graph["epics"]["e1"]["tasks"]["t2"].inputs.append(
        SpfTaskInput(id="i2", source_task_id="t-nonexistent", description="")
    )
    return valid_graph

@pytest.fixture
def simple_cycle_graph():
    """A graph with a simple A->B, B->A cycle."""
    return {
        "epics": {
            "e1": {
                "tasks": {
                    "t1": SpfTaskDocument(
                        id="t1", title="Task 1", type="task", status="pending",
                        component_ids=["c1"], implements_contract_id="k1",
                        inputs=[SpfTaskInput(id="i1", source_task_id="t2", description="")],
                        outputs=[SpfTaskOutput(id="i2", type="file", artifact_path="t1.out")],
                        content="Task content."
                    ),
                    "t2": SpfTaskDocument(
                        id="t2", title="Task 2", type="task", status="pending",
                        component_ids=["c1"], implements_contract_id="k2",
                        inputs=[SpfTaskInput(id="i2", source_task_id="t1", description="")],
                        outputs=[SpfTaskOutput(id="i1", type="file", artifact_path="t2.out")],
                        content="Task content."
                    )
                }
            }
        }
    }

@pytest.fixture
def complex_cycle_graph():
    """A graph with a longer A->B->C->A cycle."""
    return {
        "epics": {
            "e1": {
                "tasks": {
                    "t1": SpfTaskDocument(id="t1", title="T1", type="task", status="p", component_ids=["c"], implements_contract_id="k", inputs=[SpfTaskInput(id="i3", source_task_id="t3")], outputs=[SpfTaskOutput(id="i1", type="file", artifact_path="t1.out")], content="Task content."),
                    "t2": SpfTaskDocument(id="t2", title="T2", type="task", status="p", component_ids=["c"], implements_contract_id="k", inputs=[SpfTaskInput(id="i1", source_task_id="t1")], outputs=[SpfTaskOutput(id="i2", type="file", artifact_path="t2.out")], content="Task content."),
                    "t3": SpfTaskDocument(id="t3", title="T3", type="task", status="p", component_ids=["c"], implements_contract_id="k", inputs=[SpfTaskInput(id="i2", source_task_id="t2")], outputs=[SpfTaskOutput(id="i3", type="file", artifact_path="t3.out")], content="Task content."),
                }
            }
        }
    }

def test_validate_valid_graph(valid_graph):
    errors = validate_plan_graph(valid_graph)
    assert not errors

def test_validate_invalid_reference(invalid_ref_graph):
    errors = validate_plan_graph(invalid_ref_graph)
    assert len(errors) == 1
    assert "'t-nonexistent' not found" in errors[0]

def test_validate_simple_cycle(simple_cycle_graph):
    errors = validate_plan_graph(simple_cycle_graph)
    assert len(errors) == 1
    assert "Circular dependency detected" in errors[0]

def test_validate_complex_cycle(complex_cycle_graph):
    errors = validate_plan_graph(complex_cycle_graph)
    assert len(errors) == 1
    assert "Circular dependency detected" in errors[0]

def test_validate_empty_graph():
    errors = validate_plan_graph({"epics": {}})
    assert not errors
