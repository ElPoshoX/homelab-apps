At the moment this needs to be manually added to the volume on config/configuration.yaml

http:
  cors_allowed_origins:
    - https://home-assistant.elposhox.dev
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.1.0/24
    - 10.42.2.0/24
    - 10.42.3.0/24
    - 127.0.0.1
    - ::1