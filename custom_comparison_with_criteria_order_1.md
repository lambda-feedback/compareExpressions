```mermaid
flowchart TD
	N_0_0(["2+answer > response<br/>---<br/>Checks if 2+answer > response is true."])
	N_1_0["2+answer > response_TRUE<br/>---<br/>2+answer > response is true."]
	N_1_1["2+answer > response_FALSE<br/>---<br/>2+answer > response is false."]
	N_1_2["2+answer > response_UNKNOWN<br/>---<br/>2+answer > response is false."]
	N_2_0{{"END<br/>---<br/>Evaluation completed."}}
	N_1_0 --> N_2_0
	N_0_0 --> N_1_2
	N_0_0 --> N_1_0
	N_1_2 --> N_2_0
	N_0_0 --> N_1_1
	N_1_1 --> N_2_0
flowchart TD
	N_0_0(["answer <= response<br/>---<br/>Checks if answer <= response is true."])
	N_1_0["answer <= response_TRUE<br/>---<br/>answer <= response is true."]
	N_1_1["answer <= response_FALSE<br/>---<br/>answer <= response is false."]
	N_1_2["answer <= response_UNKNOWN<br/>---<br/>answer <= response is false."]
	N_2_0{{"END<br/>---<br/>Evaluation completed."}}
	N_1_0 --> N_2_0
	N_0_0 --> N_1_2
	N_0_0 --> N_1_0
	N_1_2 --> N_2_0
	N_0_0 --> N_1_1
	N_1_1 --> N_2_0
```
