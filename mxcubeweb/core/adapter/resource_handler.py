import logging
import re
from functools import reduce
from typing import (
    Callable,
    Dict,
    List,
    Type,
)

import yaml
from flask import (
    Blueprint,
    jsonify,
    make_response,
    request,
)
from pydantic.v1 import (
    BaseModel,
    ValidationError,
)


def to_openapi_path(route: str) -> str:
    """
    Adds the "{" "}" to the route arguments that OpenAPI requires

    Args:
        route(str): The route

    Returns:
        returns: the openapi path, with the {} srounding the arguments
    """
    _s = re.sub(r"<[^:]+:", "{", route)

    # Replace closing ">" with "}"
    _s = _s.replace(">", "}")

    return _s


def valid_object_id(object_id: str) -> bool:
    """
    Validates that the object_id contains only A-Z, a-z, and '.'
    Args:
        input_string (str): The string to validate.

    Returns:
        bool: True if the string is valid, False otherwise.
    """
    return bool(re.fullmatch(r"[A-Za-z.]+", object_id))


def validate_input_str(input_string: str) -> bool:
    """
    Validates that the input string contains only alphanumeric characters
    and/or dot (.).

    Args:
        input_string (str): The string to validate.

    Returns:
        bool: True if the string is valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9.]+$"
    return bool(re.match(pattern, input_string))


def assert_pydantic_arguments(func):
    """Make sure that all the arguments of func are typehinted as pydantic models"""
    annotations = func.__annotations__

    # Loop through annotations and validate parameters from the request
    for param_name, param_type in annotations.items():
        if param_name == "return":
            continue

        # Raise RuntimerError If it's not a Pydantic model
        if not issubclass(param_type, BaseModel):
            raise RuntimeError(
                f"Argument {param_name} of {func} are not a pydantic model"
            )


DEFAULT_RESPONSES = {
    "200": {"description": "Success"},
    "400": {"description": "Invalid input data"},
    "404": {"description": "Invalid or non existing object"},
    "500": {"description": "Error calling method on adapter"},
}

log = logging.getLogger("MX3.HWR")


class OpenAPISpec:
    def __init__(self, name: str, url_prefix, api_version: str, api_title: str):
        self.bp = Blueprint(name, __name__, url_prefix=url_prefix)

        self._openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": api_title, "version": api_version},
            "paths": {},
            "components": {"schemas": {}},
        }

        self.bp.add_url_rule(
            "/openapi.json", "openapi", self._serve_openapi, methods=["GET"]
        )
        self.bp.add_url_rule("/docs", "redoc_ui", self._serve_redoc_ui, methods=["GET"])
        self.bp.add_url_rule(
            "/docs_redoc", "redoc_ui", self._serve_redoc_ui, methods=["GET"]
        )
        self.bp.add_url_rule(
            "/docs_swagger", "swagger_ui", self._serve_swagger_ui, methods=["GET"]
        )
        self.bp.add_url_rule(
            "/docs_elements", "elements_ui", self._serve_elements_ui, methods=["GET"]
        )

    def _add_openapi_path(
        self,
        prefix: str,
        route: str,
        export: Dict[str, str],
        http_method: str,
        view_func,
    ):
        """Adds API endpoints to OpenAPI spec."""
        open_api_path = to_openapi_path(prefix + route)

        self._openapi_spec["paths"].setdefault(open_api_path, {})[
            http_method.lower()
        ] = {
            "summary": f"{http_method} {export['attr']}",
            "description": str(view_func.__doc__),
            "tags": [prefix],
            "parameters": [
                {
                    "name": "object_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "requestBody": {},
            "responses": dict(DEFAULT_RESPONSES),
        }

    def _add_openapi_schema(
        self, prefix: str, route: str, http_method: str, model: Type[BaseModel]
    ):
        """Adds Pydantic model definitions to OpenAPI schema."""

        open_api_path = to_openapi_path(prefix + route)
        schema_name = model.__name__

        if schema_name not in self._openapi_spec["components"]["schemas"]:
            self._openapi_spec["components"]["schemas"][schema_name] = model.schema()

        self._openapi_spec["paths"][open_api_path][http_method.lower()][
            "requestBody"
        ].update(
            {
                "description": model.__name__,
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model.__name__}"}
                    }
                },
            }
        )

    def _add_openapi_response(
        self, prefix: str, route: str, http_method: str, model: Type[BaseModel]
    ):
        """Adds response schema to OpenAPI documentation."""

        open_api_path = to_openapi_path(prefix + route)
        schema_name = model.__name__

        if schema_name not in self._openapi_spec["components"]["schemas"]:
            self._openapi_spec["components"]["schemas"][schema_name] = model.schema()

        self._openapi_spec["paths"][open_api_path][http_method.lower()]["responses"][
            "200"
        ] = {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{model.__name__}"}
                }
            },
        }

    def _serve_openapi(self):
        return jsonify(self._openapi_spec)

    def _serve_redoc_ui(self):
        """Serves the ReDoc UI for OpenAPI documentation."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redoc</title>
            <!-- needed for adaptive design -->
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">

            <!--
            Redoc doesn't change outer page styles
            -->
            <style>
            body {
                margin: 0;
                padding: 0;
            }
            </style>
        </head>
        <body>
            <redoc spec-url='openapi.json'></redoc>
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
        </body>
        </html>
        """

    def _serve_swagger_ui(self):
        """Serves the Swagger UI for OpenAPI documentation."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="SwaggerUI" />
        <title>SwaggerUI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
        </head>
        <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
        <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
            url: 'openapi.json',
            dom_id: '#swagger-ui',
            });
        };
        </script>
        </body>
        </html>
        """

    def _serve_elements_ui(self):
        """Serves the Elements UI for OpenAPI documentation."""
        return """
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
                <title>Elements in HTML</title>

                <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
                <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
            </head>
            <body>

                <elements-api
                apiDescriptionUrl="openapi.json"
                router="hash"
                />

            </body>
            </html>
        """


class AdapterResourceHandler:
    openapi_spec = OpenAPISpec("docs", "/apidocs", "1.0.0", "MXCuBE Adapter API")

    def __init__(
        self,
        name: str,
        url_prefix: str,
        adapter_dict: dict[str, object],
        app: object,
        exports: list[dict[str, str]],
        commands: list[str],
        attributes: list[str],
    ) -> None:
        """
        Initialize the AdapterResourceHandler.

        Args:
            name: Name of the blueprint.
            url_prefix: URL prefix for the blueprint.
            adapter_dict: Dictionary mapping object IDs to adapter objects.
            app: mxcube app object, providing acccess to mxcubecore and server
            exports: Predefined list of exported commands/attributes.
            commands: List of command names to export.
            attributes: List of attribute names to export.
        """
        self._bp = Blueprint(name, __name__, url_prefix=url_prefix)
        self._adapter_dict = adapter_dict
        self._server = app.server  # Store the server object to access its decorators
        self._app = app
        self._url_prefix = url_prefix
        self._exports = exports

        # Add export definitions for attributes and commands
        self._add_attribute_exports(attributes)
        self._add_command_exports(commands)

    def _create_routes_for_exports(self) -> None:
        """
        Creates Flask routes dynamically for each exported command or attribute.
        """
        for export in self._exports:
            route = (  # Dynamic route: /<object_id>/set_value
                f"/<string:object_id>/{export['attr']}"
            )
            decorators = export["decorators"]
            http_method = export["method"]

            # For the time beeing we enforce the usage of pyndatic models for arguments
            # to ensure safe vlidation of input. We rely on that those pydantic models
            # are well specified. We validate the actual data later.
            self._assert_pydantic_arguments(export)

            # Create the api doc before the view functions are created
            self._create_openapi_doc_for_view(route, export)

            # Create the view function dynamically
            view_func = self._create_view_func(route, export)

            # Apply decorators to the view function
            view_func = self._apply_decorators(view_func, decorators)

            # Register route
            self._bp.add_url_rule(
                route,
                view_func=view_func,
                methods=[http_method],
                endpoint=export["attr"],
            )
            log.debug(
                f"Registerd {route} to blueprint '{self._bp.name}' ({self._url_prefix})"
            )

    def _apply_decorators(
        self, view_func: Callable, decorators: List[Callable]
    ) -> Callable:
        """
        Applies a list of decorators to a view function.

        Args:
            view_func (Callable): The view function.
            decorators (List[Callable]): List of decorators.

        Returns:
            Callable: Decorated function.
        """
        return reduce(lambda f, decorator: decorator(f), decorators, view_func)

    def _create_view_func(self, route: str, export: Dict[str, str]) -> Callable:
        """
        Creates a Flask view function for handling requests dynamically.

        Args:
            route (str): URL route.
            export (dict): Export definition with method, attr, and decorators.

        Returns:
            Callable: The view function.
        """

        def _view_func(object_id: str, *args, **kwargs) -> any:
            # Validate object id
            if not valid_object_id(object_id):
                return jsonify({"error": f"Invalid object id '{object_id}'"}), 400

            # Check if the object_id exists in the adapter_dict
            obj = self._app.mxcubecore.get_adapter(object_id)

            if not obj:
                return jsonify({"error": f"Object '{object_id}' not found"}), 404

            # Ensure the object has the desired method
            if not hasattr(obj, export["attr"]):
                return (
                    jsonify(
                        {
                            "error": (
                                f"Method '{export['attr']}' not found on object"
                                f" '{object_id}'"
                            )
                        }
                    ),
                    404,
                )

            # Get the method and its annotations
            view_func = getattr(obj, export["attr"])
            annotations = view_func.__annotations__

            # Prepare data for all required arguments
            validated_data = {}

            # Loop through annotations and validate parameters from the request
            for param_name, param_type in annotations.items():
                if param_name == "return":  # Skip the return annotation
                    continue

                param_data = self._extract_param_data()

                if param_data is not None:
                    # If it's a Pydantic model, validate it
                    if issubclass(param_type, BaseModel):
                        try:
                            validated_data[param_name] = param_type.parse_obj(
                                param_data
                            )

                        except ValidationError as e:
                            log.exception("")
                            return (
                                jsonify({"error": f"Invalid input for {param_name}"}),
                                400,
                            )
                    elif isinstance(param_data, (str, int, float, bool)):
                        # We consider int, float and bool safe and limits handled
                        # by adapter or HardwareObject
                        validated_data[param_name] = param_data
                    elif isinstance(param_data, (str)):
                        # We consider str safe if it contains, alpha numerical
                        # characters and dot "."
                        if validate_input_str(param_data):
                            validated_data[param_name] = param_data
                        else:
                            msg = f"Invalid input for {param_name}"
                            log.error(msg)
                            return (
                                jsonify({"error": msg}),
                                400,
                            )
                    else:
                        # We could handle this case as well but we would need to be
                        # carefull with how the data is validated
                        msg = f"No model defined for '{param_name}'"
                        log.error(msg)
                        return (
                            jsonify({"error": msg}),
                            400,
                        )
                        # validated_data[param_name] = param_data

            # Call the view function with validated data
            try:
                result = view_func(**validated_data)
            except Exception as e:
                log.exception("")
                return jsonify({"error": "Error calling view function"}), 500
            else:
                # Handle and serialize the result
                return self._handle_view_result(result)

        return _view_func

    def _assert_pydantic_arguments(self, export):
        """
        Ensures the method referenced in the export uses Pydantic arguments.
        """
        obj = list(self._adapter_dict.values())[0]
        assert_pydantic_arguments(getattr(obj, export["attr"]))

    def _create_openapi_doc_for_view(self, route, export):
        """
        Adds OpenAPI documentation for a route.
        """
        # Get the first adapter object, the signature are all the same (same class) so
        # any will do for documentation porpouse
        http_method = export["method"]
        obj = list(self._adapter_dict.values())[0]
        view_func = getattr(obj, export["attr"])
        annotations = view_func.__annotations__

        # Add OpenAPI documentation root for route
        self.openapi_spec._add_openapi_path(
            self._url_prefix, route, export, http_method, view_func
        )

        # Loop through annotations add response and arguments to OpenAPI spec for route
        for param_name, param_type in annotations.items():
            if param_name == "return":
                self.openapi_spec._add_openapi_response(
                    self._url_prefix, route, http_method, param_type
                )
                continue

            # If it's a Pydantic model, document
            if issubclass(param_type, BaseModel):
                self.openapi_spec._add_openapi_schema(
                    self._url_prefix, route, http_method, param_type
                )

    def _extract_param_data(self) -> any:
        """
        Extracts parameter data from request (JSON, query params, or form).

        Returns:
            Extracted data
        """
        # Prioritize JSON body, then query params, then form data
        # We are not really using query or form data, but they are added for
        # completness
        return request.json or request.args or request.form

    def _handle_view_result(self, result: any) -> any:
        """
        Handles the result of a view function, ensuring that it is serializable and
        properly formatted.

        Returns:
            Flask Response: JSON response.
        """
        try:
            # Check if the result is a Pydantic model or any other serializable object
            if isinstance(result, BaseModel):
                # Convert Pydantic model to a dict
                result = result.dict()
            elif isinstance(result, dict):
                # If it's already a dictionary, it's ready for JSON serialization
                pass
            elif hasattr(result, "__dict__"):
                # If the result has __dict__ attribute (e.g., an object), convert to dict
                result = result.__dict__
            elif isinstance(result, (str, int, float, bool, list)):
                # If it's already a simple type, no conversion needed
                result = {"return": result}
            else:
                return (
                    jsonify(
                        {
                            "error": (
                                f"Return value of type '{type(result)}' is not"
                                " serializable"
                            )
                        }
                    ),
                    500,
                )

            # Return the result as JSON (mime-type: application/json, code: 200)
            return jsonify(result)
        except Exception:
            msg = "An error occurred while processing the response."
            log.exception(msg)
            return (
                jsonify(
                    {
                        "error": msg,
                    }
                ),
                500,
            )

    def _add_exports(self, items: list[str], http_method: str) -> None:
        """
        Add export definitions to the EXPORTS list.

        Args:
            items: The list of commands or properties to add
            http_method: The HTTP method to use, GET, POST, PUT, DELETE
        """
        for item in items:
            export = {
                "attr": item,
                "method": http_method,
                "decorators": [self._server.require_control, self._server.restrict],
            }
            if self.is_unique_export(export):
                self._exports.append(export)
            else:
                msg = f"Export {export} already exists for {self._url_prefix}"
                raise ValueError(msg)

    def is_unique_export(self, new_export):
        """
        Check if an export with the same 'attr' and 'method' already exists in the
        EXPORTS list.

        Args:
            new_export (dict): The new export to check.

        Returns:
            bool: True if unique (no duplicates), False if a duplicate exists.
        """
        for export in self._exports:
            if (
                export["attr"] == new_export["attr"]
                and export["method"] == new_export["method"]
            ):
                return False
        return True

    def _add_command_exports(self, command_list) -> None:
        """Add PUT exports for commands."""
        self._add_exports(command_list, "PUT")

    def _add_attribute_exports(self, attribute_list) -> None:
        """Add GET exports for attributes."""
        self._add_exports(attribute_list, "GET")

    def register_blueprint(self, parent_bp) -> None:
        """
        Registers the blueprint on the Flask server (server.flask). This allows the
        routes defined in the blueprint to be accessible on the server.
        """
        self._create_routes_for_exports()
        parent_bp.register_blueprint(self._bp)

        # Using try-except ot only register the documentation endpoint once
        try:
            parent_bp.register_blueprint(self.openapi_spec.bp)
        except ValueError as ex:
            pass

        log.debug(
            f"Blueprint '{self._bp.name}' ({self._url_prefix}) registered with server."
        )
