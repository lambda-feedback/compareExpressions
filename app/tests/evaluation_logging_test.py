import json
import logging

import pytest

from .. import evaluation
from ..evaluation import EvaluationError, ResponseParsingError, TaskConfigurationError, evaluation_function

# The module name depends on how pytest is run, so take it from the logger itself
LOGGER_NAME = evaluation.logger.name


def logged_events(caplog):
    events = []
    for record in caplog.records:
        if record.name == LOGGER_NAME:
            try:
                events.append(json.loads(record.getMessage()))
            except json.JSONDecodeError:
                pass
    return events


class TestEvaluationLogging():

    def test_successful_evaluation_logs_start_stages_and_end(self, caplog):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)
        evaluation_function("x+1", "1+x", {})
        events = logged_events(caplog)
        names = [event["event"] for event in events]
        assert names[0] == "evaluation_start"
        assert "stage_start" in names
        assert names[-1] == "evaluation_end"
        assert events[-1]["is_correct"] is True
        assert len({event["eval_id"] for event in events}) == 1

    def test_response_is_not_logged(self, caplog):
        caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
        response = "zzq_unique_7"
        evaluation_function(response, "y", {})
        start = logged_events(caplog)[0]
        assert not any(key.startswith("response") for key in start)
        assert response not in caplog.text

    def test_exception_is_logged_with_stage_and_reraised(self, caplog):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)
        params = {"symbols": {"where": {"latex": "where", "aliases": []}}}
        with pytest.raises(Exception, match="reserved keyword"):
            evaluation_function("x", "x", params)
        error = logged_events(caplog)[-1]
        assert error["event"] == "evaluation_error"
        assert error["stage"] == "determine_context"
        assert error["error_type"] == "TaskConfigurationError"
        assert any("determine_context" in frame for frame in error["traceback"])

    def test_exception_message_containing_response_is_not_logged(self, caplog, monkeypatch):
        caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
        response = "zzq_unique_8"

        def raise_with_response(*args, **kwargs):
            raise ValueError(f"Failed to parse: {response}")

        monkeypatch.setattr(evaluation, "create_criteria_dict", raise_with_response)
        with pytest.raises(EvaluationError) as e:
            evaluation_function(response, "y", {})
        error = logged_events(caplog)[-1]
        assert error["stage"] == "parse_criteria"
        assert error["error_type"] == "ValueError"
        assert response not in caplog.text
        assert response not in str(e.value)
        assert "parse_criteria" in str(e.value)
        assert error["eval_id"] in str(e.value)
        assert e.value.__cause__ is None
        assert e.value.__suppress_context__ is True

    def test_task_configuration_error_is_passed_on_unchanged(self):
        params = {"symbols": {"where": {"latex": "where", "aliases": []}}}
        with pytest.raises(TaskConfigurationError) as e:
            evaluation_function("x", "x", params)
        assert str(e.value) == "`where` is a reserved keyword and cannot be used as an input symbol code."

    @pytest.mark.parametrize(
        "response, params", [
            (r"\frac{zzq_unique_9}{", {"is_latex": True}),
            (r"\frac{zzq_unique_9}{1}~\mathrm{m}/", {"is_latex": True, "physical_quantity": True}),
        ]
    )
    def test_unparsable_latex_response_raises_value_error(self, caplog, response, params):
        # The base layer returns ValueError as an unprocessable submission (HTTP 422) instead of an internal error (HTTP 500)
        caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
        with pytest.raises(ResponseParsingError) as e:
            evaluation_function(response, "x", params)
        assert isinstance(e.value, ValueError)
        assert logged_events(caplog)[-1]["stage"] == "parse_latex"
        assert "zzq_unique_9" not in caplog.text
        assert "zzq_unique_9" not in str(e.value)
        assert e.value.__cause__ is None
        assert e.value.__suppress_context__ is True

    def test_params_not_mutated(self):
        params = {"strict_syntax": False, "symbols": {}}
        evaluation_function("x+1", "1+x", params)
        assert params == {"strict_syntax": False, "symbols": {}}
