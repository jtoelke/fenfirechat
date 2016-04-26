class ChatRoom:

    def __init__(self, name, user):
        self.name = name
        self.users = [user]
        self.moderators = [user]

    def len_users(self):
        return len(self.users)

    def add_user(self, user):
        self.users.append(user)
        self.users.sort()

    def remove_user(self, user):
        if user in self.users:
            self.users.remove(user)
        if user in self.moderators:
            self.moderators.remove(user)

    def has_mod(self, user):
        return user in self.moderators

    def give_mod(self, user):
        if user in self.users:
            self.moderators.append(user)
            return True
        else:
            return False
