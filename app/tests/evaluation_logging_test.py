import json
import logging

import pytest

from app.evaluation import evaluation_function


def logged_events(caplog):
    events = []
    for record in caplog.records:
        if record.name == "app.evaluation":
            try:
                events.append(json.loads(record.getMessage()))
            except json.JSONDecodeError:
                pass
    return events


class TestEvaluationLogging():

    def test_successful_evaluation_logs_start_stages_and_end(self, caplog):
        caplog.set_level(logging.INFO, logger="app.evaluation")
        evaluation_function("x+1", "1+x", {})
        events = logged_events(caplog)
        names = [event["event"] for event in events]
        assert names[0] == "evaluation_start"
        assert "stage_start" in names
        assert names[-1] == "evaluation_end"
        assert events[-1]["is_correct"] is True
        assert len({event["eval_id"] for event in events}) == 1

    def test_response_is_not_logged(self, caplog):
        caplog.set_level(logging.DEBUG, logger="app.evaluation")
        response = "zzq_unique_7"
        evaluation_function(response, "y", {})
        start = logged_events(caplog)[0]
        assert start["response_length"] == len(response)
        assert "response" not in start
        logged_text = "\n".join(record.getMessage() for record in caplog.records)
        assert response not in logged_text

    def test_exception_is_logged_with_stage_and_reraised(self, caplog):
        caplog.set_level(logging.INFO, logger="app.evaluation")
        params = {"symbols": {"where": {"latex": "where", "aliases": []}}}
        with pytest.raises(Exception, match="reserved keyword"):
            evaluation_function("x", "x", params)
        error = logged_events(caplog)[-1]
        assert error["event"] == "evaluation_error"
        assert error["stage"] == "determine_context"
        assert "reserved keyword" in error["error_message"]

    def test_params_not_mutated(self):
        params = {"strict_syntax": False, "symbols": {}}
        evaluation_function("x+1", "1+x", params)
        assert params == {"strict_syntax": False, "symbols": {}}
