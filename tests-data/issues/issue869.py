# Install PyWebview before running this test
# But need Qt installed on the system...

import webview

webview.create_window('Hello world', 'http://localhost:61208/')
webview.start()
