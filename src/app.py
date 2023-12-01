from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from data.database import Database
from modules.pdf_processor import pdf_processor
from modules.store_manager import store_manager
from modules.embedding_types import embedding_types
from modules.chat_chain import chat_chain
from data.database import Database
from modules.globals import pdf_files_dir
from modules.helpers import UserSchema, RoleSchema, UserFeedbackSchema, UploadedDocSchema, check_password

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})

vector_store_manager = store_manager(embedding_type=embedding_types.OPENAIEMBEDDINGS)
    
database = Database()
database.init()

processor = pdf_processor(db=database, store=vector_store_manager)
processor.process(pdf_files_dir=pdf_files_dir)

chain = chat_chain(store=vector_store_manager)

@app.route('/user-feedback', methods=['GET', 'POST'])
def get_user_feedbacks():
    if request.method == 'POST':
        body = request.json
        feedback = body["user_id"]
        user_id = body["feedback"]
        return jsonify(UserFeedbackSchema().dump(database.create_user_feedback(user_id, feedback)))
    else:
        return jsonify(UserFeedbackSchema(many=True).dump(database.get_user_feedbacks()))
    
@app.route('/user-feedback/archive', methods=['PUT'])
def archive_user_feedback():
    print(request.args)
    user_feedback_id = request.args["user_feedback_id"]
    return jsonify(UserFeedbackSchema().dump(database.update_user_feedback(user_feedback_id, True)))

@app.route('/role', methods=['GET'])
def get_roles():
    return jsonify(RoleSchema(many=True).dump(database.get_roles()))

@app.route('/user', methods=['GET', 'PUT'])
def users():
    if request.method == 'PUT':
        body = request.json
        user_id = body["user_id"]
        role = body["role"]
        return jsonify(UserSchema().dump(database.update_user(user_id, role)))
    else:
        return jsonify(UserSchema(many=True).dump(database.get_users()))
    
@app.route('/user/custom-instructions', methods=['PUT'])
def update_custom_instructions():
    if request.method == 'PUT':
        body = request.json
        user_id = body["user_id"]
        custom_instruction = body["custom_instruction"]
        
        updated_user = jsonify(UserSchema().dump(database.update_custom_instruction(user_id, custom_instruction)))
        chain.reset_chat(custom_instructions=custom_instruction)
        return updated_user
    
    return jsonify("Error failed to update user custom instructions")

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        body = request.json
        username = body["username"]
        password = body["password"]
        
        user = database.get_user(username)
        
        if check_password(password, user.password):
            return jsonify(UserSchema().dump(user))
        
        return jsonify("Error failed to login")
    
@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        body = request.json
        username = body["username"]
        password = body["password"]
        
        user = database.create_user(username, password)
        
        if user:
            return jsonify(UserSchema().dump(user))
        
        return jsonify("Error failed to register")
    
@app.route('/document', methods=['GET', 'POST', 'DELETE'])
def document():
    if request.method == 'GET':
        return jsonify(UploadedDocSchema(many=True).dump(database.get_uploaded_docs()))
    elif request.method == 'POST':
        body = request.json
        username = body["username"]
        password = body["password"]
        
        user = database.create_user(username, password)
        
        if check_password(password, user.password):
            return jsonify(UserSchema().dump(user))
        
    return jsonify("Error failed to register")
    
@app.route('/chat', methods=['GET'])
def chat():
    if request.method == 'GET':
        user_id = request.args["user_id"]
        query = request.args["query"]
        
        return Response(chain.new_query_stream(query), mimetype='text/plain')
        
    return jsonify("Error failed to get chat response")

if __name__ == '__main__':
    app.run()