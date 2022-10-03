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
# from flask_cors import logging

config = dotenv_values(".env")
# this instance is our WSGI app
app = flask.Flask("__name__")
app.config['MONGO_URI'] = config["DB_CONNECTION"]
CORS(app)
mongo = PyMongo(app)
# logging.getLogger('flask_cors').level = logging.DEBUG
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
            print(self.rightAnswer)
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


@socketio.on('connect')
def connect():
    print('HI you have connected with sid ' + str(request.sid))

# print(type(mongo))


@socketio.on('create_room')
def create_room(data):
    print(data)
    # print(data)
    wordnik = Wordnik()
    words = wordnik.get_random_words(
        hasDictionaryDef="true", maxLength=8, limit=2)
    print(words)
    user = data['username']
    operation = data['operation']
    room = '-'.join(words)
    print(room)
    # shortenedRoom = room[:6]
    # print(shortenedRoom)
    join_room(room)

    # print(socketio.rooms.keys())
    send(str(user) + ' ' + str(room),  to=room)
    mongo.db.Rooms.insert_one({'roomId': room, 'operation': operation, 'users': [
        {"username": user, "quizSubmitted": "false"}]})

# @socketio.on('join_existingroom')
# def join_room(data):
#     print("wow")


@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    print(str(username) + ' is leaving room ' + str(room))
    leave_room(room)
    send(str(username) + ' has left the room.', to=room)


@socketio.on('submit_quiz')
def submit_quiz(data):
    print(data)
    emit()


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
