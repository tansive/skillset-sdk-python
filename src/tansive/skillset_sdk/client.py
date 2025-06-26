"""Tansive SkillSet SDK Client

Provides the primary client interface for interacting with the Tansive SkillSet service over
Unix domain sockets. Handles skill invocation, context access, and skill discovery with
built-in connection management, retries, and error handling.
"""

import json
import socket
import time
import http.client
from urllib.parse import urlencode
from typing import Any, Dict, List, Optional
import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
from dataclasses import dataclass
import contextlib

from .exceptions import (
    TansiveError,
    TansiveConnectionError,
    TansiveTimeoutError,
    TansiveAPIError,
    TansiveRetryError,
    TansiveValidationError,
)

# DEFAULT_SOCKET_NAME = "tangent.service"


@dataclass
class SkillInvocation:
    """Represents a request to invoke a skill.

    Attributes:
        session_id (str): Unique identifier for the session.
        invocation_id (str): Unique identifier for this invocation.
        skill_name (str): Name of the skill to be invoked.
        args (Dict[str, Any]): Arguments passed to the skill.
    """

    session_id: str
    invocation_id: str
    skill_name: str
    args: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the invocation to a dictionary for API requests."""
        return {
            "session_id": self.session_id,
            "invocation_id": self.invocation_id,
            "skill_name": self.skill_name,
            "args": self.args,
        }


@dataclass
class SkillResult:
    """Represents the result of a skill invocation.

    Attributes:
        invocation_id (str): ID of the invocation this result is for.
        output (Dict[str, Any]): Output data from the skill execution.
    """

    invocation_id: str
    output: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Create a SkillResult instance from API response data."""
        return cls(invocation_id=data["invocation_id"], output=data["output"])


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over Unix domain socket for local IPC with Tansive service."""

    def __init__(self, socket_path: str, timeout: float):
        super().__init__("unix", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        """Establish connection to the Unix domain socket with error handling."""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        try:
            self.sock.connect(self.socket_path)
        except socket.timeout as e:
            self.sock.close()
            raise TansiveTimeoutError(f"Connection timed out: {e}")
        except socket.error as e:
            self.sock.close()
            raise TansiveConnectionError(f"Failed to connect to socket: {e}")
        except Exception as e:
            self.sock.close()
            raise TansiveError(f"Unexpected error during connection: {e}")


class SkillSetClient:
    """Client for interacting with the Tansive SkillSet service.

    Handles communication over Unix domain sockets with automatic retries and error handling.
    The session_id and invocation_id parameters should be reused from the initial skill
    invocation context provided by the Tansive service.

    Parameters:
        socket_path (str): Path to Unix domain socket provided by Tansive service.
        dial_timeout (float): Connection timeout in seconds. Defaults to 5.0.
        max_retries (int): Maximum retry attempts for failed requests. Defaults to 3.
        retry_delay (float): Delay between retries in seconds. Defaults to 0.1.
    """

    def __init__(
        self,
        socket_path: str,
        dial_timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        if not socket_path:
            raise TansiveValidationError("socket path is required")

        self.socket_path = socket_path
        self.dial_timeout = dial_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _make_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        ctx: Optional[Any] = None,
    ) -> Any:
        """Make an HTTP request to the Unix domain socket with retry logic.

        Internal method handling connection management and automatic retries.
        """
        last_err = None

        for _ in range(self.max_retries):
            try:
                conn = UnixHTTPConnection(self.socket_path, timeout=self.dial_timeout)

                if body is not None:
                    body_bytes = json.dumps(body).encode("utf-8")
                    headers = {"Content-Type": "application/json"}
                else:
                    body_bytes = None
                    headers = {}

                conn.request(method, path, body_bytes, headers)

                with contextlib.closing(conn.getresponse()) as resp:
                    if resp.status != 200:
                        resp_body = resp.read().decode("utf-8")
                        raise TansiveAPIError(
                            f"{path} failed: {resp_body}",
                            status_code=resp.status,
                            response_body=resp_body,
                        )

                    try:
                        return json.loads(resp.read().decode("utf-8"))
                    except json.JSONDecodeError as e:
                        raise TansiveAPIError(f"Invalid JSON in response: {e}")

            except (TansiveConnectionError, TansiveTimeoutError) as e:
                last_err = e
                time.sleep(self.retry_delay)
                continue
            except TansiveAPIError:
                raise
            except Exception as e:
                last_err = TansiveError(f"Unexpected error: {e}")
                time.sleep(self.retry_delay)
                continue
            finally:
                conn.close()

        raise TansiveRetryError(
            f"failed to {method} {path} after {self.max_retries} retries",
            last_error=last_err,
        )

    def invoke_skill(
        self,
        session_id: str,
        invocation_id: str,
        skill_name: str,
        args: Dict[str, Any],
        ctx: Optional[Any] = None,
    ) -> SkillResult:
        """Invoke a skill with the given parameters.

        Parameters:
            session_id (str): Session identifier from Tansive service.
            invocation_id (str): Invocation identifier from Tansive service.
            skill_name (str): Name of the skill to invoke.
            args (Dict[str, Any]): Arguments to pass to the skill.
            ctx (Optional[Any]): Optional context for the invocation.

        Returns:
            SkillResult: Output from the skill execution.

        Raises:
            TansiveValidationError: If required parameters are missing.
            TansiveError: For any other invocation errors.
        """
        if not session_id or not invocation_id or not skill_name:
            raise TansiveValidationError(
                "session_id, invocation_id, and skill_name are required"
            )

        invocation = SkillInvocation(
            session_id=session_id,
            invocation_id=invocation_id,
            skill_name=skill_name,
            args=args,
        )

        try:
            result = self._make_request(
                "POST", "/skill-invocations", invocation.to_dict(), ctx
            )
            return SkillResult.from_dict(result)
        except TansiveError:
            raise
        except Exception as e:
            raise TansiveError(f"Failed to invoke skill: {e}")

    def get_skills(
        self, session_id: str, ctx: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Get available skills for the given session.

        Parameters:
            session_id (str): Session identifier from Tansive service.
            ctx (Optional[Any]): Optional context for the request.

        Returns:
            List[Dict[str, Any]]: Available skills and their configurations.

        Raises:
            TansiveValidationError: If session_id is missing.
            TansiveError: For any other request errors.
        """
        if not session_id:
            raise TansiveValidationError("session_id is required")

        try:
            query = urlencode({"session_id": session_id})
            return self._make_request("GET", f"/skills?{query}", ctx=ctx)
        except TansiveError:
            raise
        except Exception as e:
            raise TansiveError(f"Failed to get skills: {e}")

    def get_context(
        self, session_id: str, invocation_id: str, name: str, ctx: Optional[Any] = None
    ) -> Any:
        """Get context data for a specific invocation.

        Parameters:
            session_id (str): Session identifier from Tansive service.
            invocation_id (str): Invocation identifier from Tansive service.
            name (str): Name of the context to retrieve.
            ctx (Optional[Any]): Optional context for the request.

        Returns:
            Any: The requested context data.

        Raises:
            TansiveValidationError: If required parameters are missing.
            TansiveError: For any other request errors.
        """
        if not session_id or not invocation_id or not name:
            raise TansiveValidationError(
                "session_id, invocation_id, and name are required"
            )

        try:
            query = urlencode(
                {"session_id": session_id, "invocation_id": invocation_id, "name": name}
            )
            return self._make_request("GET", f"/context?{query}", ctx=ctx)
        except TansiveError:
            raise
        except Exception as e:
            raise TansiveError(f"Failed to get context: {e}")

    def close(self) -> None:
        """Close the client. No-op for socket-based clients."""
        pass
