from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
import threading
import chatroom

class Chat(LineReceiver):

    lock = threading.Lock()
    rooms = {}
    MAXLEN_NAME = 64

    def __init__(self, users):
        self.users = users
        self.name = None
        self.state = "INTRO"
        self.room = None

    def connectionMade(self):
        self.sendLine("Welcome to the fenfiresong chat server\nLogin Name?")

    def connectionLost(self, reason):
        if self.room:
            self.command_leave()
        if self.name in self.users:
            del self.users[self.name]

    def lineReceived(self, line):
        if self.state == "INTRO":
            self.handle_INTRO(line)
        else:
            self.handle_CHAT(line)

    def handle_INTRO(self, name):
        name = name.strip()
        if name in self.users:
            self.sendLine("Sorry, name taken.\nLogin Name?")
            return
        reason = self.name_sanity_check(name, "user")
        if reason:
            self.sendLine("{}Login Name?".format(reason))
            return
        self.sendLine("Welcome, {}!".format(name))
        self.name = name
        self.users[name] = self
        self.state = "CHAT"

    def handle_CHAT(self, message):
        if message.startswith("/rooms"):
            self.command_rooms()
        elif message.startswith("/join"):
            self.command_join(message)
        elif message.startswith("/leave"):
            self.command_leave()
        elif message.startswith("/quit"):
            self.command_quit()
        elif self.room == None:
            self.sendLine("You're not in any room! Use /rooms to list active rooms and use /join <room> to enter or create a room.")
        else:
            message = "<{}> {}".format(self.name, message)
            self.sendLine(message)
            self.send_to_chatroom(message)

    def name_sanity_check(self, name, nametype):
        reason = None
        if name == "":
            reason = "The {} name can't be empty.\n".format(nametype)
        if name.startswith("/"):
            reason =  "Don't start the {} name with /, that's used for commands.\n".format(nametype)
        if len(name) > Chat.MAXLEN_NAME:
            reason = "The {} name can't be longer than {} characters.\n".format(nametype, Chat.MAXLEN_NAME)
        return reason

    def send_to_chatroom(self, message):
        with Chat.lock:
            recipients = self.room.users
        for name in recipients:
            if name != self.name:
                self.users[name].sendLine(message)

    def command_rooms(self):
        message = "Active rooms are:\n"
        with Chat.lock:
            for room in Chat.rooms:
                message += " * {} ({})\n".format(Chat.rooms[room].name, len(Chat.rooms[room].users))
        message += "end of list."
        self.sendLine(message)

    def command_join(self, message):
        roomname = message.replace("/join", "", 1).strip()
        reason = self.name_sanity_check(roomname, "room")
        if reason:
            self.sendLine("{}Which room do you want to join? Use /rooms to list active rooms or use /join <room> with an unused name to create a new one.".format(reason))
            return
        if self.room:
            self.command_leave()
        with Chat.lock:
            if roomname in Chat.rooms.keys():
                Chat.rooms[roomname].users.append(self.name)
            else:
                room = chatroom.ChatRoom(roomname, self.name)
                Chat.rooms[roomname] = room
            self.room = Chat.rooms[roomname]
            message = "entering room: {}\n".format(roomname)
            for user in Chat.rooms[roomname].users:
                message += " * {}".format(user)
                if user == self.name:
                    message += " (** this is you)\n"
                else:
                    message += "\n"
        message += "end of list."
        self.sendLine(message)
        message = " * new user joined chat: {}".format(self.name)
        self.send_to_chatroom(message)

    def command_leave(self):
        message = " * user has left the chat: {}".format(self.name)
        self.send_to_chatroom(message)
        message = " * user has left the chat: {} (** this is you)".format(self.name)
        self.sendLine(message)
        with Chat.lock:
            self.room.users.remove(self.name)
            if len(self.room.users) == 0:
                del Chat.rooms[self.room.name]
        self.room = None

    def command_quit(self):
        self.sendLine("BYE")
        self.transport.loseConnection()

class ChatFactory(Factory):

    def __init__(self):
        self.users = {} # maps user names to Chat instances

    def buildProtocol(self, addr):
        return Chat(self.users)


reactor.listenTCP(11042, ChatFactory())
reactor.run()
