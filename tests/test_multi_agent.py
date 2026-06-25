import pytest

class TestAgentSystem:
    def test_agent_has_required_attributes(self):
        agent = {"name": "ResearchAgent", "role": "researcher", "tools": ["web_search", "summarize"], "status": "idle"}
        assert "name" in agent
        assert "role" in agent
        assert "tools" in agent

    def test_task_routing(self):
        def route_task(task_type):
            routing = {"research": "ResearchAgent", "code": "CodeAgent", "review": "ReviewAgent"}
            return routing.get(task_type, "GeneralAgent")
        assert route_task("research") == "ResearchAgent"
        assert route_task("unknown") == "GeneralAgent"

    def test_agent_message_passing(self):
        messages = []
        def send(agent, msg):
            messages.append({"to": agent, "content": msg})
        send("CodeAgent", "Write a function to sort a list")
        assert len(messages) == 1
        assert messages[0]["to"] == "CodeAgent"

    def test_task_completion_status(self):
        task = {"id": "task_001", "status": "pending", "result": None}
        task["status"] = "completed"
        task["result"] = "Done"
        assert task["status"] == "completed"
        assert task["result"] is not None

    def test_agent_tool_validation(self):
        available_tools = {"web_search", "summarize", "code_execute", "file_read"}
        agent_tools = ["web_search", "summarize"]
        for tool in agent_tools:
            assert tool in available_tools

class TestOrchestration:
    def test_pipeline_sequential_execution(self):
        pipeline = ["fetch_data", "process", "summarize", "output"]
        executed = []
        for step in pipeline:
            executed.append(step)
        assert executed == pipeline

    def test_error_propagation(self):
        def agent_run(task):
            if not task:
                raise ValueError("Task cannot be empty")
            return "success"
        with pytest.raises(ValueError):
            agent_run("")

    def test_result_aggregation(self):
        results = [{"agent": "A", "output": "Result 1"}, {"agent": "B", "output": "Result 2"}]
        combined = " | ".join(r["output"] for r in results)
        assert "Result 1" in combined and "Result 2" in combined
