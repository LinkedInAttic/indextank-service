import traceback
import sys
class ViewErrorLoggingMiddleware:
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        self.view_name = view_func.__name__
    def process_exception(self, request, exception):
        print '=' * 60
        print '[ERROR] exception in view "%s"' % self.view_name
        traceback.print_exc(file=sys.stdout)
        print '=' * 60
