from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit, send
import eventlet
import random
import json
import flask
from random_word import Wordnik
from flask_cors import CORS
from flask_pymongo import PyMongo
from dotenv import dotenv_values
from collections import MutableMapping
import certifi
ca = certifi.where()

config = dotenv_values(".env")
# this instance is our WSGI app
app = flask.Flask("__name__")
app.config['MONGO_URI'] = config['DB_CONNECTION']
CORS(app)
mongo = PyMongo(app, tlsCAFile=ca)

# wrapping our flask app in SocketIO
socketio = SocketIO(app, async_mode='eventlet',
                    logger=True, cors_allowed_origins='*')
# make sure to use @ decorator in front
# of routes


class Question:

    def __init__(self, operator, num1, num2):
        if (operator == 'addition'):
            self.rightAnswer = num1 + num2
            self.operand = "+"
        if (operator == 'subtraction'):
            self.rightAnswer = num1 - num2
            self.operand = "-"
        if (operator == 'multiplication'):
            self.rightAnswer = num1 * num2
            # print(self.rightAnswer)
            self.operand = "•"
        if (operator == 'division'):
            num2 = makeNum2Pos(num2)
            num1 = find_evenly_divisible(num1, num2)
            self.rightAnswer = round(num1/num2)
            self.operand = "÷"
        self.question = 'What is the result ' + \
            ' of ' + str(num1) + ' ' + self.operand + ' ' + str(num2) + '?'
        self.answerChoices = AnswerChoices(self.rightAnswer, operator)

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
# if num2 is 0, this function will return a non zero value
# necessary because we cannot divide by 0 (undefined)


def makeNum2Pos(num2):
    while (num2 == 0):
        num2 = random.randrange(-25, 25)
    return num2


def find_evenly_divisible(num1, num2):

    if (num1 % num2 != 0):
        num1 = num2 * random.randint(1, 25)
    return num1

# gets rid of repeat answer choices


def makeSureNotEqual(randnum1, randnum2, randnum3, rightAnswer):
    # for cases where at least one of the random numbers == rightAnswer
    # but are not equal to each othder
    while (randnum1 == rightAnswer or randnum2 == rightAnswer or randnum3 == rightAnswer):
        randnum1 = random.randrange(rightAnswer-15, rightAnswer+15)
        randnum2 = random.randrange(rightAnswer-15, rightAnswer+15)
        randnum3 = random.randrange(rightAnswer-15, rightAnswer+15)

    # if at least one set of randomnumbers are equal
    while (randnum1 == randnum2 or randnum2 == randnum3 or randnum1 == randnum3):
        randnum1 = random.randrange(rightAnswer-15, rightAnswer+15)
        randnum2 = random.randrange(rightAnswer-15, rightAnswer+15)
        randnum3 = random.randrange(rightAnswer-15, rightAnswer+15)
        # checks to see if any of the new numbers are equal to the right answer
        while (randnum1 == rightAnswer):
            randnum1 = random.randrange(rightAnswer-15, rightAnswer+15)

        while (randnum2 == rightAnswer):
            randnum2 = random.randrange(rightAnswer-15, rightAnswer+15)
        while (randnum3 == rightAnswer):
            randnum3 = random.randrange(rightAnswer-15, rightAnswer+15)

    listRandNums = [randnum1, randnum2, randnum3]
    return listRandNums


class AnswerChoices:
    def __init__(self, rightAnswer, operator):

        random1 = random.randrange(rightAnswer-15, rightAnswer+15)
        random2 = random.randrange(rightAnswer-15, rightAnswer+15)
        random3 = random.randrange(rightAnswer-15, rightAnswer+15)
        answerChoices = makeSureNotEqual(
            random1, random2, random3, rightAnswer)
        self.answerChoice1 = answerChoices[0]
        self.answerChoice2 = answerChoices[1]
        self.answerChoice3 = rightAnswer
        self.answerChoice4 = answerChoices[2]

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

        # need to have some negative answer choices


@app.route("/")
def rootRoute():
    return "This API generates 10 questions for a Math quiz", 200


@app.route("/quiz/<operation>")
async def createQuiz(operation):
    if operation == None:
        operation = 'addition'
    allQuestions = []
    for x in range(0, 10):
        randomNum1 = random.randint(-25, 25)
        randomNum2 = random.randint(-25, 25)
        indivQuestion = Question(operation, randomNum1, randomNum2).toJSON()
        allQuestions.append(indivQuestion)
    return allQuestions


@app.route("/joinquiz/<lobbycode>")
def joinQuiz(lobbycode):
    roomData = mongo.db.Rooms.find_one({'roomId': lobbycode})
    # quiz = roomData['quiz']
    return roomData['quiz']


@app.route("/users/<lobbyCode>")
def allusers(lobbyCode):
    roomData = roomData = mongo.db.Rooms.find_one({'roomId': lobbyCode})
    users = roomData['users']
    return users


@socketio.on('connect')
def connect():
    print('HI you have connected with sid ' + str(request.sid))

# print(type(mongo))


@socketio.on('create_room')
def create_room(data):
    print(data)
    wordnik = Wordnik()
    words = wordnik.get_random_words(
        hasDictionaryDef="true", maxLength=8, limit=2)
    user = data['username']
    operation = data['operation']
    room = '-'.join(words)
    print(room)
    join_room(room)
    send(str(user) + ' ' + str(room))
    mongo.db.Rooms.insert_one({'roomId': room, 'operation': operation, 'users': [
                              {"username": user, "quizSubmitted": "false", "score": 0}], 'quiz': {}})


@socketio.on('quiz_start')
def quiz_start(data):
    print(data)
    quiz = data['quiz']
    roomId = data['msg']
    if (quiz[0]['question'] == ''):
        emit('blank_quiz')
    else:
        print(data)
        emit(200)
        mongo.db.Rooms.find_one_and_update(
            {'roomId': roomId}, {'$set': {'quiz': quiz}})


@socketio.on('existing_room')
def existing_room(data):
    print(data)
    newUser = data['username']
    lobby = data['lobbyCode']
    roomData = mongo.db.Rooms.find_one({'roomId': lobby})
    users = roomData['users']
    quiz = roomData['quiz']
    users.append({'username': newUser, 'quizSubmitted': 'false', "score": 0})
    # print(users)
    newList = [lobby] + users
    join_room(lobby)
    send(str(newUser) + ' has joined the room', to=lobby)
    mongo.db.Rooms.find_one_and_update(
        {'roomId': lobby}, {'$set': {'users': users}})


@socketio.on('leave')
def on_leave(data):
    print(data)
    username = data['username']
    room = data['room']
    print(str(username) + ' is leaving room ' + str(room))
    leave_room(room)
    users = mongo.db.Rooms.find_one({'roomId': room})['users']
    filtered = list(filter(
        lambda user: user['username'] != username, users))
    print(filtered)
    mongo.db.Rooms.find_one_and_update(
        {'roomId': room}, {'$set': {'users': filtered}}
    )
    updatedUsers = mongo.db.Rooms.find_one({'roomId': room})['users']
    if (len(updatedUsers) < 1):
        mongo.db.Rooms.find_one_and_delete({'roomId': room})
    send(str(username) + ' has left the room.', to=room)


@socketio.on('submit_quiz')
def submit_quiz(data):
    # print(data)
    user = data['username']
    lobby = data['lobbyCode']
    score = data['score']
    # print(user, lobby, score)
    users = mongo.db.Rooms.find_one({'roomId': lobby})['users']
    print(users)
    # specificUser = list(filter(lambda person: user.username == user, users))
    # print(specificUser)
    # [specificUser][0]['quizSubmitted'] = "true"
    # [specificUser][0]['score'] = score
    # print(specificUser)
    otherUsers = list(filter(lambda person: person['username'] != user, users))
    # print(otherUsers)
    # newList = specificUser + otherUsers
    # print(newList)
    otherUsers.append(
        {'username': user, "quizSubmitted": "true", "score": score})
    mongo.db.Rooms.find_one_and_update(
        {'roomId': lobby}, {'$set': {'users': otherUsers}})
    updatedUsers = users = mongo.db.Rooms.find_one({'roomId': lobby})['users']
    # print(updatedUsers)
    submittedUsers = list(
        filter(lambda person: person['quizSubmitted'] == "true", updatedUsers))
    # print(submittedUsers)
    if (len(submittedUsers) == len(updatedUsers)):
        scoresList = []
        for obj in submittedUsers:
            scoresList.append([obj['username'], obj['score']])
        print(scoresList)
        emit('all_submit', scoresList, to=lobby)
    else:
        send('submitted')


@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')


@socketio.on_error()        # Handles the default namespace
def error_handler(e):
    pass


if __name__ == '__main__':
    # socketio.run starts up the webserver
    socketio.run(app, port=8000)

# wsgi.server(eventlet.listen("",8080))
