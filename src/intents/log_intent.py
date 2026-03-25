from utils.response import build_response

def handle_log_intent(event):
    text = event['request']['intent']['slots']['freeText']['value']
    
    print(f"[LogIntent] User said: {text}")

    return build_response(f"Got it. You said: {text}")