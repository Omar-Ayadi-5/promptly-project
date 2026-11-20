from bson import ObjectId
from flask import Blueprint, jsonify, request
from ...common.authentication import token_required
from ...common.context import get_service

blueprint = Blueprint('voice', __name__)


@blueprint.route('/api/save_voice_message', methods=['POST'])
@token_required
def save_voice(current_user_id):
    # Check the declared body size before parsing multipart data.
    uploaded_file = request.files.get('file')
    user_id = request.form.get('userId')
    if user_id != current_user_id:
        return jsonify({'error': 'unauthorized access'}), 403
    if uploaded_file is None:
        return jsonify({'error': 'No file part'}), 400
    if not uploaded_file.filename:
        return jsonify({'error': 'No selected file'}), 400
    chat_id = request.form.get('chatId')
    model = request.form.get('model')
    if not chat_id or not ObjectId.is_valid(chat_id) or not model:
        return jsonify({'error': 'A valid chat and model are required'}), 400
    file_bytes = uploaded_file.read()
    if not file_bytes:
        return jsonify({'error': 'The recording is empty'}), 400
    transcript = get_service('voice').save_voice(uploaded_file.filename, file_bytes, user_id, chat_id, model)
    if transcript.status == 'error':
        return jsonify({'error': 'Unable to transcribe the recording. Please try again.'}), 502
    return jsonify({'transcript': transcript.text}), 200
