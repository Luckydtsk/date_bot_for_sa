from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    gender = State()
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


class AdminBroadcast(StatesGroup):
    waiting_text = State()
