class ChatRoom:

    def __init__(self, name, user):
          self.name = name
          self.users = [user]

    def add_user(self, user):
        self.users.apend(user)
        self.users.sort()

    def remove_user(self, user):
        self.users.remove(user)
        return len (self.users)
