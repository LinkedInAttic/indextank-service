import traceback
from lib import flaptor_logging
from django.http import HttpResponse

logger = flaptor_logging.get_logger('error_logging')

class ViewErrorLoggingMiddleware:
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        self.view_name = view_func.__name__
    def process_exception(self, request, exception):
        logger.error('UNEXPECTED EXCEPTION in view "%s". Exception is: %s', self.view_name, repr(traceback.print_exc()))
        return HttpResponse('{"status":"ERROR", "message":"Unexpected error."}')
