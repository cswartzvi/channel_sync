from rich.console import Console
from rich.control import Control
from rich.segment import ControlType


print("Hello")
print("World")

console = Console()
control = Control.move(y=-1)
console.control(control)
console.


print("Done")