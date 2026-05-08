from dataclasses import dataclass, field
from enum import StrEnum
from typing import List

class ScopeNames(StrEnum):
    START_SCREEN = "Start Screen"
    NAVIGATION_SCREEN = "Navigation Screen"
    SINGLE_CAPTURE_SCREEN = "Single Capture Screen"
    MULTI_CAPTURE_SCREEN = "Multi Capture Screen"
    COLLAGE_MAKER_SCREEN = "Collage Maker Screen"
    GALLERY = "Gallery"
    PHOTO_DETAILS_SCREEN = "Photo Details Screen"
    PRINT_DIALOG = "Print Dialog"
    SHARE_SCREEN = "Share Screen"
    QR_DIALOG = "QR Dialog"
    LANGUAGE_DIALOG = "Language Dialog"

_EMPTY_SCHEMA = { "type": "object", "additionalProperties": False }

@dataclass
class Action:
    name: str
    title: str
    description: str
    examples: List[str]
    next_state: ScopeNames
    input_schema: dict = field(default_factory=_EMPTY_SCHEMA)

@dataclass
class Scope:
    description: str
    actions: List[Action] = field(default_factory=list)

SCOPE_STATES = {
    ScopeNames.START_SCREEN: Scope(
        description="The initial 'attract' mode of the application. Displays a 'Touch to Start' prompt.",
        actions=[
            Action(
                name="start",
                title="Start",
                description="Begin the photo booth experience.",
                examples=["start", "begin", "let's go", "proceed", "continue"],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.NAVIGATION_SCREEN: Scope(
        description="The central hub for all user activities. Provides access to capture modes, the gallery, and settings.",
        actions=[
            Action(
                name="single_photo",
                title="Single Photo",
                description="Take a single photo.",
                examples=["single", "single capture", "single photo", "single picture", "take a photo"],
                next_state=ScopeNames.SINGLE_CAPTURE_SCREEN
            ),
            Action(
                name="collage",
                title="Collage",
                description="Shoot multiple photos and create a collage from them.",
                examples=["collage", "collage capture", "collage photo", "collage picture", "take a collage"],
                next_state=ScopeNames.MULTI_CAPTURE_SCREEN
            ),
            Action(
                name="gallery",
                title="Gallery",
                description="View the previously captured photos.",
                examples=["gallery", "view gallery", "see photos", "browse images"],
                next_state=ScopeNames.GALLERY
            ),
            Action(
                name="open_language_dialog",
                title="Language",
                description="Open the language selection dialog.",
                examples=["language", "change language", "select language", "set language", "open language settings"],
                next_state=ScopeNames.LANGUAGE_DIALOG
            )
        ]
    ),
    ScopeNames.SINGLE_CAPTURE_SCREEN: Scope(
        description="An autonomous capture flow for a single photo. Includes a countdown and live preview."
    ),
    ScopeNames.MULTI_CAPTURE_SCREEN: Scope(
        description="An autonomous multi-capture flow for collages. Includes countdowns for each capture."
    ),
    ScopeNames.COLLAGE_MAKER_SCREEN: Scope(
        description="The workspace for assembling a custom collage from captured images.",
        actions=[
            Action(
                name="select_pictures",
                title="Select Pictures",
                description="Choose pictures to include in the collage. 1-indexed.",
                examples=["select picture {selected}", "select the {selected} and {selected} picture"],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN,
                input_schema={ "type": "object", "properties": { "selected": { "type": "array", "items": { "type": "integer", "minimum": 1, "maximum": 4 }, "minItems": 0, "maxItems": 4 }}, "description": "The indices of the selected pictures, 1-indexed", "required": ["selected"], "additionalProperties": False }
            ),
            Action(
                name="continue",
                title="Continue",
                description="Proceed to the share screen.",
                examples=["continue", "next", "done", "finished"],
                next_state=ScopeNames.SHARE_SCREEN
            ),
            Action(
                name="select_all_pictures",
                title="Select All Pictures",
                description="Select all captured pictures",
                examples=["select all pictures", "all of them", "use all pictures"],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN
            )
        ]
    ),
    ScopeNames.GALLERY: Scope(
        description="An archive overview of all saved collage outputs.",
        actions=[
            Action(
                name="open_latest_picture",
                title="Open Latest Picture",
                description="View the most recently captured picture.",
                examples=["latest", "most recent", "last photo"],
                next_state=ScopeNames.PHOTO_DETAILS_SCREEN
            ),
            Action(
                name="back",
                title="Back",
                description="Return to the navigation screen.",
                examples=["back", "previous", "go back"],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.PHOTO_DETAILS_SCREEN: Scope(
        description="A detailed view of a selected gallery image with options to print or share.",
        actions=[
            Action(
                name="back",
                title="Back",
                description="Return to the gallery screen.",
                examples=["back", "previous", "go back"],
                next_state=ScopeNames.GALLERY
            ),
            Action(
                name="get_qr",
                title="Get QR Code",
                description="Show the user a QR code in a pop-up dialog.",
                examples=["get qr code", "show qr code", "share photo"],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="open_print_dialog",
                title="Print",
                description="Open the print dialog.",
                examples=["print", "print photo", "i want to print"],
                next_state=ScopeNames.PRINT_DIALOG
            )
        ]
    ),
    ScopeNames.PRINT_DIALOG: Scope(
        description="A dialog for configuring the print job, such as number of copies.",
        actions=[
            Action(
                name="cancel",
                title="Cancel",
                description="Presses the cancel button in the print dialog.",
                examples=["cancel", "stop", "abort"],
                next_state=ScopeNames.SHARE_SCREEN
            ),
            Action(
                name="set_print_count",
                title="Set Print Count",
                description="Sets the number of copies to print.",
                examples=["print five pictures", "set three copies"],
                next_state=ScopeNames.PRINT_DIALOG,
                input_schema={ "type": "object", "properties": {"count": { "type": "integer", "minimum": 1, "maximum": 5 }}, "required": ["count"], "additionalProperties": False}
            ),
            Action(
                name="print",
                title="Print",
                description="Presses the print button in the print dialog.",
                examples=["print", "print it", "let's print"],
                next_state=ScopeNames.PRINT_DIALOG
            )
        ]
    ),
    ScopeNames.SHARE_SCREEN: Scope(
        description="The final screen for a new capture, offering printing and sharing options.",
        actions=[
            Action(
                name="retake",
                title="Retake Photo",
                description="Retake the current photo.",
                examples=["retake", "take again", "try again"],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN
            ),
            Action(
                name="get_qr",
                title="Get QR Code",
                description="Show the user a QR code in a pop-up dialog.",
                examples=["get qr code", "share photo"],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="open_print_dialog",
                title="Print Photo",
                description="Open the print dialog.",
                examples=["print", "print photo"],
                next_state=ScopeNames.PRINT_DIALOG
            ),
            Action(
                name="continue",
                title="Continue",
                description="Proceed to the start screen.",
                examples=["continue", "done", "finished"],
                next_state=ScopeNames.START_SCREEN
            )
        ]
    ),
    ScopeNames.LANGUAGE_DIALOG: Scope(
        description="A pop-up dialog where the user can change the application's language locale.",
        actions=[
            Action(
                name="set_language",
                title='Set Language',
                description='Change the application language.',
                examples=['set language to {language_code}'],
                next_state=ScopeNames.NAVIGATION_SCREEN,
                input_schema={ "type": "object", "properties": { "language_code": { "enum": ["en", "nl", "de", "fr"], "description": "The ISO 639-1 code" } }, "required": ["language_code"], "additionalProperties": False }
            ),
            Action(
                name="close",
                title='Close Dialog',
                description='Close the language dialog.',
                examples=['close', 'cancel', 'dismiss'],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.QR_DIALOG: Scope(
        description="A dialog displaying a QR code for the user to download their image.",
        actions=[
            Action(
                name="redo_upload",
                title='Redo Upload',
                description="Start the upload process again to get a new QR code.",
                examples=['redo upload', 'upload again'],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="close",
                title='Close Dialog',
                description='Close the QR sharing dialog.',
                examples=['done', 'close', 'dismiss'],
                next_state=ScopeNames.SHARE_SCREEN
            )
        ]
    )
}
