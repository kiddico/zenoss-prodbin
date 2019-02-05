# Broker settings
broker_url = "amqp://zenoss:zenoss@localhost:5672//zenoss"

# List of modules to import when the Celery worker starts
imports = ("Products.Jobber.jobs",)

# Using Redis to store task state and results
result_backend = "redis://localhost/1"

# Worker configuration
worker_concurrency = 2
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 100

# Task settings
task_acks_late = True

# Event settings
worker_send_task_events = True
task_send_sent_event = True

# Log settings
# worker_hijack_root_logger = False
