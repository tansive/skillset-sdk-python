# Tansive™ Python SkillSet SDK

The official Python SkillSet™ SDK for Tansive™ - Open Platform for Secure AI Agents.

## Installation

```bash
pip install tansive-skillset-sdk
```

## Quick Start

```python
from tansive.skillset_sdk import SkillSetClient
import uuid

# Initialize the client with a Unix domain socket path
client = SkillSetClient("/tmp/tangent.sock")

# Invoke a skill
result = client.invoke_skill(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    invocation_id="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    skill_name="example.echo",
    args={"message": "Hello from Tansive!"}
)

print(result.output)

# Retrieve skills
skills = client.get_skills(session_id="550e8400-e29b-41d4-a716-446655440000")
print(skills)

# Fetch context
context = client.get_context(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    invocation_id="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    name="model-config"
)
print(context)
```

## Documentation

For detailed documentation, visit [docs.tansive.io](https://docs.tansive.io).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
