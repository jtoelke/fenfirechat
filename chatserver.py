from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

class Chat(LineReceiver):

    def __init__(self, users):
        self.users = users
        self.name = None
        self.state = "INTRO"

    def connectionMade(self):
        self.sendLine("Welcome to the fenfiresong chat server\nLogin Name?")

    def connectionLost(self, reason):
        if self.name in self.users:
            del self.users[self.name]

    def lineReceived(self, line):
        if self.state == "INTRO":
            self.handle_INTRO(line)
        else:
            self.handle_CHAT(line)

    def handle_INTRO(self, name):
        if name in self.users:
            self.sendLine("Sorry, name taken.\nLogin Name?")
            return
        self.sendLine("Welcome, {}!".format(name))
        self.name = name
        self.users[name] = self
        self.state = "CHAT"

    def handle_CHAT(self, message):
        message = "<{}> {}".format(self.name, message)
        for name, protocol in self.users.iteritems():
            protocol.sendLine(message)


class ChatFactory(Factory):

    def __init__(self):
        self.users = {} # maps user names to Chat instances

    def buildProtocol(self, addr):
        return Chat(self.users)


reactor.listenTCP(11042, ChatFactory())
reactor.run()
