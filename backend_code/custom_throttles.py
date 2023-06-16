from rest_framework import throttling

class UserSignUpThrottle(throttling.AnonRateThrottle):
  scope = 'user_signup'

  def allow_request(self, request, view):
    return super().allow_request(request, view)
