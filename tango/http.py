"Tango's WSGI wrappers for request and response."

from flask import Request as BaseRequest
from flask import Response as BaseResponse


# Currently just class declarations to provide an extensible namespace.

class Request(BaseRequest):
    "The request object contains all incoming request data."


class Response(BaseResponse):
    "The response object contains the body, headers, status code, ..."
