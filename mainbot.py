import http.server
import json
import asyncio
from botbuilder.schema import (Activity, ActivityTypes, ChannelAccount)
from botframework.connector import ConnectorClient
from botframework.connector.auth import (MicrosoftAppCredentials,
                                         JwtTokenValidation, SimpleCredentialProvider)

APP_ID = ''
APP_PASSWORD = ''
PORT = 9000

class BotRequestHandler(http.server.BaseHTTPRequestHandler):
    
    # these are diseases and their symptoms 
    f_symptoms = ['fever', 'cough', 'sore throat', 'runny', 'nose', 'muscle', 'headaches', 'fatigue']
    d_symptoms = ['loose', 'watery', 'stools', 'cramps', 'fever', 'blood', 'bloating', 'nausea', 'bowel']

    @staticmethod
    def __create_reply_activity(request_activity, text):
        return Activity(
            type=ActivityTypes.message,
            channel_id=request_activity.channel_id,
            conversation=request_activity.conversation,
            recipient=request_activity.from_property,
            from_property=request_activity.recipient,
            text=text,
            service_url=request_activity.service_url)

    def __handle_conversation_update_activity(self, activity):
        self.send_response(202)
        self.end_headers()
        if activity.members_added[0].id != activity.recipient.id:
            credentials = MicrosoftAppCredentials(APP_ID, APP_PASSWORD)
            reply = BotRequestHandler.__create_reply_activity(activity, 'Hello, welcome to Doctor Bot.\n'
                                                              + 'If you are not feeling well, tell me whats wrong, '
                                                              + 'and I will try to help you out')
            connector = ConnectorClient(credentials, base_url=reply.service_url)
            connector.conversations.send_to_conversation(reply.conversation.id, reply)

    def __handle_message_activity(self, activity):
        self.send_response(200)
        self.end_headers()
        credentials = MicrosoftAppCredentials(APP_ID, APP_PASSWORD)
        connector = ConnectorClient(credentials, base_url=activity.service_url)
        reply = BotRequestHandler.__create_reply_activity(activity, self.predict_illness(activity.text))
        connector.conversations.send_to_conversation(reply.conversation.id, reply)

    def __handle_authentication(self, activity):
        credential_provider = SimpleCredentialProvider(APP_ID, APP_PASSWORD)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(JwtTokenValidation.authenticate_request(
                activity, self.headers.get("Authorization"), credential_provider))
            return True
        except Exception as ex:
            self.send_response(401, ex)
            self.end_headers()
            return False
        finally:
            loop.close()

    def __unhandled_activity(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(str(body, 'utf-8'))
        activity = Activity.deserialize(data)

        if not self.__handle_authentication(activity):
            return

        # Handle when someone join the server
        if activity.type == ActivityTypes.conversation_update.value:
            self.__handle_conversation_update_activity(activity)
        # handle when someone write a message on server 
        elif activity.type == ActivityTypes.message.value:
            self.__handle_message_activity(activity)
        # handle unknown error
        else:
            self.__unhandled_activity()

    def predict_illness(self, str):
        f_count = 0 #flu symthoms count
        d_count = 0 #diarhea symthoms count
        for fs in self.f_symptoms:
            if fs in str:
                f_count += 1
        for ds in self.d_symptoms:
            if ds in str:
                d_count += 1
        if(f_count > d_count):
            return 'You might have a flu.\n' + 'Check this link for a Flu treatment: https://www.mayoclinic.org/diseases-conditions/flu/diagnosis-treatment/drc-20351725'
        elif(d_count > f_count):
            return 'You might have a diarrhea.\n' + 'Check this link for a Diarrhea treatment: https://www.emedicinehealth.com/diarrhea/article_em.htm'
        else:
            return 'Sorry, we dont really know your illness based on your synthoms'


try:
    print('Starting server on: ' + 'http://localhost:' + str(PORT))
    SERVER = http.server.HTTPServer(('localhost', PORT), BotRequestHandler)
    SERVER.serve_forever()
except KeyboardInterrupt:
    SERVER.socket.close()
