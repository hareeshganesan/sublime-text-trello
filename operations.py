import sublime

try:
    from executable import Executable
    from trello_collection import TrelloCollection
    from trello_cache import TrelloCache
    from card_options import CardOptions
    from custom_actions import CustomActions
except ImportError:
    from .executable import Executable
    from .trello_collection import TrelloCollection
    from .trello_cache import TrelloCache
    from .card_options import CardOptions
    from .custom_actions import CustomActions

class BaseOperation(Executable):
    def __init__(self, trello_element, previous_operation = None):
        self.custom_actions = CustomActions(self)
        self.trello_element = trello_element
        self.previous_operation = previous_operation
        self.after_init()

    def after_init(self):
        pass
        
    def items(self):
        self.set_collection()
        return self.custom_actions.encapsulate(self.collection.names())

    def set_collection(self):
        self.collection = TrelloCollection(self.trello_element, self.trello_element_property())

    def trello_element_property(self):
        return ""
        
    def trello_element_name(self):
        return self.__class__.__name__.replace("Operation", "")

    def callback(self, index):
        if self.custom_actions.has(index):
            self.custom_actions.call(index)
        else:
            self.command.defer(lambda: self.execute_command(index - self.custom_actions.len()))

    def get_name(self, label="Name"):
        self.command.input(label, self.deferred_add)

    def deferred_add(self, text = None, start = None):
        if text:
            self.command.defer(lambda: self.base_add(text, start))

    def base_add(self, text, start = None):
        self.add(text, start)
        self.restart()

    def add(self, text, start = None):
        pass

    def deferred_delete(self, card_id):
        self.command.defer(lambda: self.base_delete(card_id))

    def base_delete(self, card_id):
        self.delete(card_id)
        self.restart()

    def delete(card_id):
        pass

    def restart(self):
        self.trello_element.reload()
        self.reexecute()

    def execute_command(self, index):
        if self.collection.has(index):
            Operation = self.next_operation_class()
            Operation(self.collection.find(index), self).execute(self.command)

    def next_operation_class(self):
        pass

    def open_in_browser(self):
        if(hasattr(self, 'command')):
            self.command.defer(super().open_in_browser)
        else:
            super().open_in_browser()

class BoardOperation(BaseOperation):
    def after_init(self):
        self.custom_actions.remove("..")

    def trello_element_property(self):
        return "boards"

    def next_operation_class(self):
        return ListOperation

    def add(self, text, start = None):
        self.trello_element.add_board(text)

class ListOperation(BaseOperation):
    def trello_element_property(self):
        return "lists"

    def next_operation_class(self):
        return CardOperation

    def add(self, text, start = None):
        self.trello_element.add_list(text)

class CardOperation(BaseOperation):
    def after_init(self):
        self.custom_actions.remove("Open in Browser")
        self.custom_actions.rename("Create Card", "Quick create card")
        self.custom_actions.add("Create card with description", self.create_with_description)
        TrelloCache.set(self)

    def trello_element_property(self):
        return "cards"

    def next_operation_class(self):
        return CardOptions


    def create_with_description(self, label=""):
        first  = "Replace this with the card name. The card will be saved when this tab is closed, leave this tab empty to cancel"
        middle = "Replace this with the card description, it can be multiline."
        last   = "You can create as many cards as you want, just split them by the card_delimiter (from the settings) and a newline." 
        message = "%s %s\n\n%s\n%s" % (label, first, middle, last)
        self.command.output_editable(message, self)

    def full_add(self, content):
        for card in self.split_cards(content):
            name, description = self.split_card_contents(card)
            self.add(name, description)
        self.restart()
        
    def add(self, text, start = None, description = None):
        card = self.trello_element.add_card(text, description)
        self.command.view.run_command("insert", {"characters": "Trello #"+card._id+": "+text})

    def delete(self, card_id):
        card = self.trello_element._conn.get_card(card_id)
        card.delete()
        self.command.view.run_command("expand_selection", {"to": "line"})
        self.command.view.run_command("left_delete")


    def split_cards(self, content):
        return content.split(self.command.card_delimiter + "\n") if self.command.card_delimiter else [content]

    def split_card_contents(self, content):
        splitted = content.split("\n\n", 1)
        return (splitted[0], splitted[1] if len(splitted) > 1 else None)