from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    gender = State()
    edu_level = State()
    faculty = State()
    height = State()
    dance = State()
    about = State()
    photo = State()
    contact = State()


class EditProfile(StatesGroup):
    choose_field = State()
    name = State()
    gender = State()
    faculty = State()
    height = State()
    dance = State()
    about = State()
    photo = State()
    contact = State()
    confirm_delete = State()
    confirm_refill = State()


class Feed(StatesGroup):
    browsing = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()


class AdminPickUser(StatesGroup):
    waiting = State()  # data: admin_action = view|ban|unban
