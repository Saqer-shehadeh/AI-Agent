import argparse
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from functions.call_function import available_functions, call_function
from prompts import system_prompt


def main():
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")

    parser = argparse.ArgumentParser(description="AI coding agent")
    parser.add_argument("user_input", type=str, help="User Prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    client = genai.Client(api_key=api_key)

    messages: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=args.user_input)])
    ]

    for _ in range(20):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                tools=[available_functions],
                system_instruction=system_prompt,
                temperature=0,
            ),
        )

        if response.usage_metadata is None:
            raise RuntimeError("API request failed: response usage_metadata is missing")

        if args.verbose:
            print(f"User prompt: {args.user_input}")
            print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
            print(f"Response tokens: {response.usage_metadata.candidates_token_count}")

        if response.candidates:
            for candidate in response.candidates:
                messages.append(candidate.content)

        if not response.function_calls:
            print("Final response:")
            print(response.text)
            return

        function_responses = []

        for function_call_part in response.function_calls:
            function_call_result = call_function(function_call_part, args.verbose)

            if not function_call_result.parts:
                raise Exception("Function call result has no parts")

            function_response = function_call_result.parts[0].function_response

            if function_response is None:
                raise Exception("Function call result has no function_response")

            if function_response.response is None:
                raise Exception("Function response has no response")

            function_responses.append(function_call_result.parts[0])

            if args.verbose:
                print(f"-> {function_response.response}")

        messages.append(types.Content(role="user", parts=function_responses))

    print("Error: Agent reached maximum iterations without producing a final response")
    sys.exit(1)


if __name__ == "__main__":
    main()
