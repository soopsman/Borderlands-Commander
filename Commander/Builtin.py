import unrealsdk #type: ignore
from unrealsdk import GetEngine, FindObject, CallPostEdit #type: ignore

from Mods import ModMenu #type: ignore

from . import Commander, Configurator

from typing import Sequence
import math
from fractions import Fraction

Positions: ModMenu.Options.Hidden = ModMenu.Options.Hidden(
    Caption="Positions",
    StartingValue={}
)
DamageNumbers: ModMenu.Options.Hidden = ModMenu.Options.Hidden(
    Caption="DamageNumbers",
    StartingValue=True
)
MaxSavePositions: ModMenu.Options.Spinner = ModMenu.Options.Spinner(
    Caption="Max Save Positions",
    Description="The number of save positions.",
    Choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"],
    StartingValue="3"
)
ClientTeleporting: ModMenu.Options.Spinner = ModMenu.Options.Spinner(
    Caption="Client Teleporting",
    Description="Should clients in multiplayer be allowed to teleport their location, or should their location be teleported with the host.",
    Choices=["Allow", "With Host", "None"],
    StartingValue="Allow"
)
ClientSpeedPermissions: ModMenu.Options.Boolean = ModMenu.Options.Boolean(
    Caption="Client Speed Permissions",
    Description="Should clients in multiplayer be allowed to modify the speed of the game.",
    StartingValue=False
)


Options: Sequence[ModMenu.Options.Base] = (
    Positions, DamageNumbers, MaxSavePositions, ClientTeleporting, ClientSpeedPermissions
)

def PC():
    return GetEngine().GamePlayers[0].Actor

def _IsClient() -> bool:
    return GetEngine().GetCurrentWorldInfo().NetMode == 3


def Popup(message, seconds = 2.0) -> None:
    """Presents a "training" message to the user with the given string."""
    # Get the graphics object for our player controller's HUD.
    HUDMovie = PC().GetHUDMovie()

    # If there is no graphics object, we cannot display feedback.
    if HUDMovie is None:
        return

    # We will be displaying the message for two *real time* seconds.
    duration = seconds * _DefaultGameInfo.GameSpeed
    # Clear any previous message that may be displayed.
    HUDMovie.ClearTrainingText()
    # Present the training message as per the method's signature:
    #     AddTrainingText(string MessageString, string TitleString, float Duration, Color DrawColor, string HUDInitializationFrame, bool PausesGame, float PauseContinueDelay, PlayerReplicationInfo Related_PRI1, optional bool bIsntActuallyATrainingMessage, optional WillowPlayerController.EBackButtonScreen StatusMenuTab, optional bool bMandatory)
    HUDMovie.AddTrainingText(message, "Commander", duration, (), "", False, 0, PC().PlayerReplicationInfo, True)


_DefaultGameInfo = FindObject("WillowCoopGameInfo", "WillowGame.Default__WillowCoopGameInfo")
"""A reference to the WillowCoopGameInfo template object."""
# We use this for managing game speed, as WorldInfo objects pull their TimeDilation from it.


def ApplyGameSpeed(speed):
    GetEngine().GetCurrentWorldInfo().TimeDilation = _DefaultGameInfo.GameSpeed = speed
    Popup("Game Speed: " + str(Fraction(speed)))
    Commander.Instance.ClientApplyGameSpeed(speed)


def _HalveGameSpeed():
    speed = _DefaultGameInfo.GameSpeed
    if speed > 0.0625:
        speed /= 2
        if _IsClient():
            Commander.Instance.ServerRequestGameSpeed(speed)
        else:
            ApplyGameSpeed(speed)


def _DoubleGameSpeed():
    speed = _DefaultGameInfo.GameSpeed
    if speed < 32:
        speed *= 2
        if _IsClient():
            Commander.Instance.ServerRequestGameSpeed(speed)
        else:
            ApplyGameSpeed(speed)


def _ResetGameSpeed():
    speed = _DefaultGameInfo.GameSpeed
    if speed != 1.0:
        speed = 1.0
        if _IsClient():
            Commander.Instance.ServerRequestGameSpeed(speed)
        else:
            ApplyGameSpeed(speed)
    else:
        Popup("Game Speed: 1")


# For toggling damage numbers, we locate the particle system object resposible for emitting them.
DamageNumberParticleSystem = FindObject("ParticleSystem", "FX_CHAR_Damage_Matrix.Particles.Part_Dynamic_Number")
# The SDK cannot currently replace individual FArray members with nulls, so we create two of our own
# copies of its emitter array; one that emits damage numbers, and one that doesn't.
DamageNumberEmitters = list(DamageNumberParticleSystem.Emitters)
NoDamageNumberEmitters = list(DamageNumberParticleSystem.Emitters)
# The first two particles in the emitter array are the ones responsible for damage numbers, so we
# replace them with nulls in the "no damage number" array.
NoDamageNumberEmitters[0] = None
NoDamageNumberEmitters[1] = None

def _ToggleDamageNumbers():
    DamageNumbers.CurrentValue = not DamageNumbers.CurrentValue
    ModMenu.SaveModSettings(Commander.Instance)

    CallPostEdit(False)
    if DamageNumbers.CurrentValue:
        DamageNumberParticleSystem.Emitters = DamageNumberEmitters
        Popup("Damage Numbers: On")
    else:
        DamageNumberParticleSystem.Emitters = NoDamageNumberEmitters
        Popup("Damage Numbers: Off")
    CallPostEdit(True)


_Position = 0


def _IncrementPosition():
    _SelectPosition(1)


def _DecrementPosition():
    _SelectPosition(-1)


def _SelectPosition(increment: int):
    global _Position
    _Position = _Position + increment
    if _Position >= int(MaxSavePositions.CurrentValue):
        _Position = 0

    if _Position < 0:
        _Position = int(MaxSavePositions.CurrentValue) - 1

    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)

    name = f"{_Position + 1}"
    positions = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue));
    if len(positions) <= _Position:
        Popup(f"Selected Position {name}")
        return

    position = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))[_Position]
    if position != None and "Name" in position:
        name = position["Name"]
    Popup(f"Selected Position {name}")


def _DisplayPositions():
    global _Position

    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)
    positions = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))

    activePositions = []
    for i in range(int(MaxSavePositions.CurrentValue)):
        if len(positions) > i and positions[i] != None:
            name = f"Position {i + 1}"
            if "Name" in positions[i]:
                name = positions[i]["Name"]
            activePositions.append(name)
        
    line = ""
    popup = ""
    for name in activePositions:
        if len(line) == 0:
            line = name
        else:
            if len(f"{line} / {name}") <= 27:
                line = f"{line} / {name}"
            else:
                if len(popup) > 0:
                    popup = f"{popup}\n{line}"
                else:
                    popup = line
                line = name
    
    if len(line) > 0:
        popup = f"{popup}\n{line}"

    Popup(popup if len(popup) > 0 else "No saved positions", 5)


def _GetPosition(PC):
    location = PC.Pawn.Location
    rotation = PC.Rotation
    return {
        "X": location.X, "Y": location.Y, "Z": location.Z,
        "Pitch": rotation.Pitch, "Yaw": rotation.Yaw
    }


def ApplyPosition(PC, position):
    location = position["X"], position["Y"], position["Z"]
    rotation = position["Pitch"], position["Yaw"], 0

    _, vehicle = PC.IsUsingVehicleEx(True)
    if vehicle is None:
        PC.NoFailSetPawnLocation(PC.Pawn, location)
    else:
        pawn = vehicle.GetPawnToTeleport()
        pawn.Mesh.SetRBPosition(location);
        pawn.Mesh.SetRBRotation(rotation);
    PC.ClientSetRotation(rotation)


def _SavePosition():
    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)

    positions = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))

    global _Position
    if _Position >= int(MaxSavePositions.CurrentValue):
        _Position = 0

    if len(positions) != int(MaxSavePositions.CurrentValue):
        updatePositions = [None] * int(MaxSavePositions.CurrentValue)
        for i in range(int(MaxSavePositions.CurrentValue)):
            if len(positions) > i and positions[i] != None:
                updatePositions[i] = positions[i]
        positions = updatePositions

    positions[_Position] = _GetPosition(PC())

    Positions.CurrentValue[mapName] = positions
    ModMenu.SaveModSettings(Commander.Instance)

    Popup(f"Saved Position {_Position + 1}")


def _PromptForName():
    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)

    global _Position
    if _Position >= int(MaxSavePositions.CurrentValue):
        _Position = 0

    position = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))[_Position]
    if position is None:
        Popup(f"Position {_Position + 1} Not Saved")
    else:
        if "Name" in position:
            Configurator._CustomSavePositionName(position["Name"])
        else:
            Configurator._CustomSavePositionName(f"Position {_Position + 1}")


def _NamePosition(name):
    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)

    positions = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))

    if name == "":
        positions[_Position]["Name"] = f"{_Position + 1}"
    else:
        positions[_Position]["Name"] = f"{name} ({_Position + 1})"

    Positions.CurrentValue[mapName] = positions
    ModMenu.SaveModSettings(Commander.Instance)

    Popup(f"Saved Name {name} ({_Position + 1})")


def _RestorePosition():
    mapName = GetEngine().GetCurrentWorldInfo().GetMapName(True)

    global _Position
    if _Position >= int(MaxSavePositions.CurrentValue):
        _Position = 0

    position = Positions.CurrentValue.get(mapName, [None] * int(MaxSavePositions.CurrentValue))[_Position]
    if position is None:
        Popup(f"Position {_Position + 1} Not Saved")

    elif _IsClient():
        Commander.Instance.ServerRequestPosition(position, name=str(_Position + 1))

    else:
        ApplyPosition(PC(), position)
        name = position["Name"] if "Name" in position else f"{_Position + 1}"
        Popup(f"Restored Position {name}")

        if ClientTeleporting.CurrentValue == "With Host":
            for PRI in GetEngine().GetCurrentWorldInfo().GRI.PRIArray:
                if PRI.Owner is not None:
                    ApplyPosition(PRI.Owner, position)
            Commander.Instance.ClientApplyPosition(position, name="")


def _MoveForward():
    position = _GetPosition(PC())

    # Convert our pitch and yaw from the game's units to radians.
    pitch = position["Pitch"] / 65535 * math.tau
    yaw   = position["Yaw"  ] / 65535 * math.tau

    position["Z"] += math.sin(pitch) * 250
    position["X"] += math.cos(yaw) * math.cos(pitch) * 250
    position["Y"] += math.sin(yaw) * math.cos(pitch) * 250

    if _IsClient():
        Commander.Instance.ServerRequestPosition(position, name=None)
    else:
        ApplyPosition(PC(), position)


def ApplyPlayersOnly(playersOnly):
    GetEngine().GetCurrentWorldInfo().bPlayersOnly = playersOnly
    Popup("World Freeze: " + ("On" if playersOnly else "Off"))
    Commander.Instance.ClientApplyPlayersOnly(playersOnly)

def _TogglePlayersOnly():
    playersOnly = not GetEngine().GetCurrentWorldInfo().bPlayersOnly
    if _IsClient():
        Commander.Instance.ServerRequestPlayersOnly(playersOnly)
    else:
        ApplyPlayersOnly(playersOnly)


Keybinds: Sequence[ModMenu.Keybind] = (
    ModMenu.Keybind("Halve Game Speed",      "LeftBracket",  OnPress=_HalveGameSpeed     ),
    ModMenu.Keybind("Double Game Speed",     "RightBracket", OnPress=_DoubleGameSpeed    ),
    ModMenu.Keybind("Reset Game Speed",      "None",         OnPress=_ResetGameSpeed     ),
    ModMenu.Keybind("Toggle World Freeze",   "Backslash",    OnPress=_TogglePlayersOnly  ),
    ModMenu.Keybind("Toggle Damage Numbers", "Quote",        OnPress=_ToggleDamageNumbers),
    ModMenu.Keybind("Save Position",         "Period",       OnPress=_SavePosition       ),
    ModMenu.Keybind("Name Position",         "N",            OnPress=_PromptForName      ),
    ModMenu.Keybind("Restore Position",      "Comma",        OnPress=_RestorePosition    ),
    ModMenu.Keybind("Next Position",         "Slash",        OnPress=_IncrementPosition  ),
    ModMenu.Keybind("Previous Position",     "BackSpace",    OnPress=_DecrementPosition  ),
    ModMenu.Keybind("Display Positions",     "P",            OnPress=_DisplayPositions  ),
    ModMenu.Keybind("Teleport Forward",      "Up",           OnPress=_MoveForward        ),
)

def KeybindExists(name: str) -> bool:
    for keybind in Keybinds:
        if keybind.Name == name:
            return True
    return False
