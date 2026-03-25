from intents.log_intent import handle_log_intent
from utils.response import build_response

def lambda_handler(event, context):
    try:
        request_type = event['request']['type']

        if request_type == "LaunchRequest":
            return build_response("Welcome. You can tell me to remember something.")

        elif request_type == "IntentRequest":
            intent = event['request']['intent']['name']

            if intent == "LogActivityIntent":
                return handle_log_intent(event)

            elif intent == "AMAZON.HelpIntent":
                return build_response("You can say, remember that something.")

            elif intent in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
                return build_response("Goodbye", end_session=True)

        return build_response("I didn't get that.")

    except Exception as e:
        print("ERROR:", str(e))
        return build_response("Something went wrong.")