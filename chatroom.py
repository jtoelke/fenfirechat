class ChatRoom:

    def __init__(self, name, user):
          self.name = name
          self.users = [user]
          self.moderators = [user]

    def add_user(self, user):
        self.users.apend(user)
        self.users.sort()

    def remove_user(self, user):
        if user in self.users:
            self.users.remove(user)
        if user in self.moderators:
            self.moderators.remove(user)
        return len (self.users)

    def has_mod(self, user):
        if user in self.moderators:
            return True
        else:
            return False
