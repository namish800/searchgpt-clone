from langchain_openai import ChatOpenAI


class LLMFactory:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

    def get_llm_by_name(self, model_name: str):
        return self.llm

    def complete_with_structured_output(self, response_model: dict, prompt: str):
        self.llm.with_structured_output(response_model)
        return self.llm.invoke(prompt)

    def complete(self, prompt: str):
        return self.llm.invoke(prompt);