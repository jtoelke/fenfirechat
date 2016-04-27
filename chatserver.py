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
        '''override from LineReceiver'''
        self.sendLine("Welcome to the fenfiresong chat server\nLogin Name?")

    def connectionLost(self, reason):
        '''override from LineReceiver'''
        if self.room:
            self.command_leave()
        if self.name in self.users:
            del self.users[self.name]

    def lineReceived(self, line):
        '''override from LineReceiver'''
        if self.state == "INTRO":
            self.handle_intro(line)
        else:
            self.handle_chat(line)

    def handle_intro(self, name):
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

    def handle_chat(self, message):
        if message == "":
            pass
        elif message.startswith("/help"):
            self.command_help()
        elif message.startswith("/rooms"):
            self.command_rooms()
        elif message.startswith("/join"):
            self.command_join(message)
        elif message.startswith("/quit"):
            self.command_quit()
        elif message.startswith("/whisper") or message.startswith("/w"):
            self.command_whisper(message)
        elif self.room == None:
            self.sendLine("You're not in any room! Use /rooms to list active rooms and use /join <room> to enter or create a room.")
        elif message.startswith("/users"):
            self.command_users()
        elif message.startswith("/leave"):
            self.command_leave()
        elif message.startswith("/me"):
            self.command_me(message)
        elif message.startswith("/mod"):
            self.command_mod(message)
        elif message.startswith("/kick"):
            self.command_kick(message)
        else:
            message = "<{}> {}".format(self.name, message)
            self.sendLine(message)
            self.send_to_chatroom(message)

# helper functions

    def name_sanity_check(self, name, nametype):
        """Check if name meets requirements, return string with reason why not or None."""
        reason = None
        if not name.isalnum():
            reason = "Please choose a {} name that consists of alphanumeric characters.\n".format(nametype)
        if len(name) > Chat.MAXLEN_NAME:
            reason = "The {} name can't be longer than {} characters.\n".format(nametype, Chat.MAXLEN_NAME)
        return reason

    def send_to_chatroom(self, message):
        """Send message to all users of a chat room but for the sender."""
        with Chat.lock:
            recipients = self.room.users
        for name in recipients:
            if name != self.name:
                self.users[name].sendLine(message)

    def mod_check(self, user):
        """Return whether a user has mod rights. Send message to user if not."""
        with Chat.lock:
            if not self.room.has_mod(self.name):
                self.sendLine("You need to be moderator to use this command.")
                return False
            else:
                return True

    def get_userlist(self, room):
        """Return a string listing the users in the given room."""
        users = ""
        with Chat.lock:
            for user in room.users:
                users += " * {}".format(user)
                if user == self.name:
                    users += " (** this is you)\n"
                else:
                    users += "\n"
        users += "end of list."
        return users

# command handling

    def command_help(self):
        message = '''Available commands are:
    /rooms to list active rooms
    /join <room> to enter or create a room
    /users to list users in your current room
    /leave to leave the room you're currently in
    /quit to disconnect from the server
    /whisper <user> <message> to send a private message to another user
    /me to perform an action, replacing /me with your user name, for example: /me dances is displayed as * user dances
    /mod <user> to give moderation rights to another user, only usable if you have moderation rights yourself
    /kick <user> [reason] to kick a user out of a channel with an optional message, only usable if you have moderation rights
        '''
        self.sendLine(message)

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
                Chat.rooms[roomname].add_user(self.name)
            else:
                room = chatroom.ChatRoom(roomname, self.name)
                Chat.rooms[roomname] = room
            self.room = Chat.rooms[roomname]
        message = "entering room: {}\n".format(roomname)
        message += self.get_userlist(self.room)
        self.sendLine(message)
        message = " * new user joined chat: {}".format(self.name)
        self.send_to_chatroom(message)

    def command_users(self):
        message = self.get_userlist(self.room)
        self.sendLine(message)

    def command_leave(self):
        message = " * user has left the chat: {}".format(self.name)
        self.send_to_chatroom(message)
        message = " * user has left the chat: {} (** this is you)".format(self.name)
        self.sendLine(message)
        with Chat.lock:
            self.room.remove_user(self.name)
            if self.room.len_users() == 0:
                del Chat.rooms[self.room.name]
        self.room = None

    def command_me(self, message):
        message = message.replace("/me", "* {}".format(self.name), 1).strip()
        self.sendLine(message)
        self.send_to_chatroom(message)

    def command_quit(self):
        self.sendLine("BYE")
        self.transport.loseConnection()

    def command_whisper(self, message):
        message_parts = message.split(None, 2)
        if len(message_parts) < 3:
            self.sendLine("To send a private message you need a recipient and a message: /w <recipient> <message>")
        else:
            recipient = message_parts[1]
            pmessage = message_parts[2]
            if recipient in self.users:
                self.users[recipient].sendLine("<{} whispers> {}".format(self.name, pmessage))
                self.sendLine("To {}: {}".format(recipient, pmessage))
            else:
                self.sendLine("Can't find user: {}".format(recipient))

    def command_mod(self, message):
        if not self.mod_check(self.name):
            return

        message_parts = message.split(None, 1)
        if len(message_parts) < 2:
            self.sendLine("No user given. Use /mod <user>")
            return

        user = message_parts[1]
        if user not in self.users:
            self.sendLine("There is no user {}.".format(user))
            return

        message = " * {} was made moderator by {}.".format(user, self.name)
        self.send_to_chatroom(message)
        self.sendLine(message)
        with Chat.lock:
            self.room.give_mod(user)

    def command_kick(self, message):
        if not self.mod_check(self.name):
            return

        message_parts = message.split(None, 2)
        if len(message_parts) < 2:
            self.sendLine("No user given. Use /kick <user> [reason]")
            return

        user = message_parts[1]
        if user not in self.users:
            self.sendLine("There is no user {}.".format(user))
            return

        if len(message_parts) > 2:
            reason = ' "{}"'.format(message_parts[2])
        else:
            reason = ""
        message = " * {} was kicked by moderator {}.{}".format(user, self.name, reason)
        self.send_to_chatroom(message)
        self.sendLine(message)
        with Chat.lock:
            self.room.remove_user(user)
            if self.room.len_users() == 0:
                del Chat.rooms[self.room.name]
        self.users[user].room = None


class ChatFactory(Factory):

    def __init__(self):
        self.users = {} # maps user names to Chat instances

    def buildProtocol(self, addr):
        return Chat(self.users)


reactor.listenTCP(11042, ChatFactory())
reactor.run()
