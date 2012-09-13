from tango.app import Tango

app = Tango.build_app('hybrid')
app.this_was_added_after_stash = 'Hello, world!'
