"""Framework-independent scheduling engine.

Import concrete functions from their owning modules. Keeping this initializer
lightweight prevents the schema layer and scheduler from forming an import
cycle.
"""
