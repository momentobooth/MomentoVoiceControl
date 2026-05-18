import re
from collections import OrderedDict
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


_EMPTY_SCHEMA = {"type": "object", "additionalProperties": False}


@dataclass
class Example:
    phrase: str
    arguments: dict = field(default_factory=dict)

    def with_example_in_phrase(self) -> "Example":
        pattern = r"\{(\w*?):(\w*?)\}"
        replacement = r"\2"
        new_phrase = re.sub(pattern, replacement, self.phrase)
        return Example(phrase=new_phrase, arguments=self.arguments)

    def to_dict(self):
        return OrderedDict({"phrase": self.phrase, "arguments": self.arguments})


@dataclass
class Action:
    name: str
    title: str
    description: str
    examples: List[Example]
    next_state: ScopeNames
    input_schema: dict = field(default_factory=lambda: _EMPTY_SCHEMA)
    input_schema_description: str = "{}"


@dataclass
class ScopeInfo:
    name: str
    description: str
    actions: List[Action] = field(default_factory=list)


SCOPE_STATES: dict[ScopeNames, ScopeInfo] = {
    ScopeNames.START_SCREEN: ScopeInfo(
        name=ScopeNames.START_SCREEN.value,
        description="The initial 'attract' mode of the application. Displays a 'Touch to Start' prompt.",
        actions=[
            Action(
                name="start",
                title="Start",
                description="Begin the photo booth experience.",
                examples=[
                    Example(phrase="start"),
                    Example(phrase="begin"),
                    Example(phrase="let's go"),
                    Example(phrase="proceed"),
                    Example(phrase="continue")
                ],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.NAVIGATION_SCREEN: ScopeInfo(
        name=ScopeNames.NAVIGATION_SCREEN.value,
        description="The central hub for all user activities. Provides access to capture modes, the gallery, and settings.",
        actions=[
            Action(
                name="single_photo",
                title="Single Photo",
                description="Take a single photo.",
                examples=[
                    Example(phrase="single"),
                    Example(phrase="single capture"),
                    Example(phrase="single photo"),
                    Example(phrase="single picture"),
                    Example(phrase="take a photo")
                ],
                next_state=ScopeNames.SINGLE_CAPTURE_SCREEN
            ),
            Action(
                name="collage",
                title="Collage",
                description="Shoot multiple photos and create a collage from them.",
                examples=[
                    Example(phrase="collage"),
                    Example(phrase="collage capture"),
                    Example(phrase="collage photo"),
                    Example(phrase="collage picture"),
                    Example(phrase="take a collage")
                ],
                next_state=ScopeNames.MULTI_CAPTURE_SCREEN
            ),
            Action(
                name="gallery",
                title="Gallery",
                description="View the previously captured photos.",
                examples=[
                    Example(phrase="gallery"),
                    Example(phrase="view gallery"),
                    Example(phrase="see photos"),
                    Example(phrase="browse images")
                ],
                next_state=ScopeNames.GALLERY
            ),
            Action(
                name="open_language_dialog",
                title="Language",
                description="Open the language selection dialog.",
                examples=[
                    Example(phrase="language"),
                    Example(phrase="change language"),
                    Example(phrase="select language"),
                    Example(phrase="set language"),
                    Example(phrase="open language settings")
                ],
                next_state=ScopeNames.LANGUAGE_DIALOG
            )
        ]
    ),
    ScopeNames.SINGLE_CAPTURE_SCREEN: ScopeInfo(
        name=ScopeNames.SINGLE_CAPTURE_SCREEN.value,
        description="An autonomous capture flow for a single photo. Includes a countdown and live preview."
    ),
    ScopeNames.MULTI_CAPTURE_SCREEN: ScopeInfo(
        name=ScopeNames.MULTI_CAPTURE_SCREEN.value,
        description="An autonomous multi-capture flow for collages. Includes countdowns for each capture."
    ),
    ScopeNames.COLLAGE_MAKER_SCREEN: ScopeInfo(
        name=ScopeNames.COLLAGE_MAKER_SCREEN.value,
        description="The workspace for assembling a custom collage from captured images.",
        actions=[
            Action(
                name="select_pictures",
                title="Select Pictures",
                description="Choose pictures to include in the collage. 1-indexed.",
                examples=[
                    Example(phrase="select picture {selected:1}, {selected:2} and {selected:4}",
                            arguments={"selected": [1, 2, 4]}),
                    Example(phrase="select picture {selected:one} and {selected:two}", arguments={"selected": [1, 2]}),
                    Example(phrase="select picture {selected:one}", arguments={"selected": [1]}),
                    Example(phrase="select the {selected:first} picture", arguments={"selected": [1]}),
                    Example(phrase="select the {selected:second} and {selected:third} picture",
                            arguments={"selected": [2, 3]}),
                    Example(phrase="select the {selected:third}, {selected:second}, and {selected:first} picture",
                            arguments={"selected": [3, 2, 1]})
                ],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN,
                input_schema={"type": "object", "properties": {
                    "selected": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 4},
                                 "minItems": 0, "maxItems": 4}},
                              "description": "The indices of the selected pictures, 1-indexed",
                              "required": ["selected"], "additionalProperties": False},
                input_schema_description='{ "selected": array of 1-indexed integers between 1 and 4, e.g., [1, 2, 4] }'
            ),
            Action(
                name="continue",
                title="Continue",
                description="Proceed to the share screen.",
                examples=[
                    Example(phrase="continue"),
                    Example(phrase="next"),
                    Example(phrase="go on"),
                    Example(phrase="proceed"),
                    Example(phrase="keep going"),
                    Example(phrase="done"),
                    Example(phrase="finished")
                ],
                next_state=ScopeNames.SHARE_SCREEN
            ),
            Action(
                name="select_all_pictures",
                title="Select All Pictures",
                description="Select all captured pictures",
                examples=[
                    Example(phrase="select all pictures"),
                    Example(phrase="select all photos"),
                    Example(phrase="select all images"),
                    Example(phrase="select all"),
                    Example(phrase="all of them"),
                    Example(phrase="all pictures"),
                    Example(phrase="use all pictures")
                ],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN
            )
        ]
    ),
    ScopeNames.GALLERY: ScopeInfo(
        name=ScopeNames.GALLERY.value,
        description="An archive overview of all saved collage outputs.",
        actions=[
            Action(
                name="open_latest_picture",
                title="Open Latest Picture",
                description="View the most recently captured picture.",
                examples=[
                    Example(phrase="latest"),
                    Example(phrase="most recent"),
                    Example(phrase="last photo"),
                    Example(phrase="last picture"),
                    Example(phrase="open latest")
                ],
                next_state=ScopeNames.PHOTO_DETAILS_SCREEN
            ),
            Action(
                name="back",
                title="Back",
                description="Return to the previous screen.",
                examples=[
                    Example(phrase="back"),
                    Example(phrase="previous"),
                    Example(phrase="go back"),
                    Example(phrase="return"),
                    Example(phrase="previous screen")
                ],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.PHOTO_DETAILS_SCREEN: ScopeInfo(
        name=ScopeNames.PHOTO_DETAILS_SCREEN.value,
        description="A detailed view of a selected gallery image with options to print or share.",
        actions=[
            Action(
                name="back",
                title="Back",
                description="Return to the gallery screen.",
                examples=[
                    Example(phrase="back"),
                    Example(phrase="previous"),
                    Example(phrase="go back")
                ],
                next_state=ScopeNames.GALLERY
            ),
            Action(
                name="share_with_qr_code_dialog",
                title="Share with QR Code",
                description="Upload the photo, generate a QR code and display it in a dialog to share the photo.",
                examples=[
                    Example(phrase="get qr code"),
                    Example(phrase="show qr code"),
                    Example(phrase="share photo")
                ],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="open_print_dialog",
                title="Open Print Dialog",
                description="Open the print dialog where options can be selected and a print job can be submitted.",
                examples=[
                    Example(phrase="print"),
                    Example(phrase="print it"),
                    Example(phrase="print photo"),
                    Example(phrase="print picture"),
                    Example(phrase="i want a print"),
                    Example(phrase="i want to print"),
                    Example(phrase="let's print")
                ],
                next_state=ScopeNames.PRINT_DIALOG
            )
        ]
    ),
    ScopeNames.PRINT_DIALOG: ScopeInfo(
        name=ScopeNames.PRINT_DIALOG.value,
        description="A dialog for configuring the print job, such as number of copies.",
        actions=[
            Action(
                name="cancel",
                title="Cancel",
                description="Presses the cancel button in the print dialog.",
                examples=[
                    Example(phrase="cancel"),
                    Example(phrase="stop"),
                    Example(phrase="abort"),
                    Example(phrase="never mind"),
                    Example(phrase="forget it"),
                    Example(phrase="close"),
                    Example(phrase="dismiss"),
                    Example(phrase="exit")
                ],
                next_state=ScopeNames.SHARE_SCREEN
            ),
            Action(
                name="set_copies",
                title="Set Copies",
                description="Sets the number of copies to print.",
                examples=[
                    Example(phrase="set copies to {copies:1}", arguments={"copies": 1}),
                    Example(phrase="make {copies:three} copies", arguments={"copies": 3}),
                    Example(phrase="change copies to {copies:four}", arguments={"copies": 4}),
                    Example(phrase="set number of copies to {copies:2}", arguments={"copies": 2})
                ],
                next_state=ScopeNames.PRINT_DIALOG,
                input_schema={"type": "object", "properties": {
                    "copies": {"type": "integer", "description": "The number of copies to print", "minimum": 1,
                               "maximum": 5}}, "required": ["copies"], "additionalProperties": False},
                input_schema_description='{ "copies": integer between 1 and 5 }'
            ),
            Action(
                name="set_size",
                title="Set Size",
                description="Sets the print size.",
                examples=[
                    Example(phrase="set print size to {size:Normal print size}",
                            arguments={"size": "Normal print size"}),
                    Example(phrase="change print size to {size:Small print size}",
                            arguments={"size": "Small print size"}),
                    Example(phrase="set size to {size:Normal print size}", arguments={"size": "Normal print size"}),
                    Example(phrase="change size to {size:Tiny print size}", arguments={"size": "Tiny print size"})
                ],
                next_state=ScopeNames.PRINT_DIALOG,
                input_schema={"type": "object", "properties": {
                    "size": {"enum": ["Normal print size", "Small print size", "Tiny print size"],
                             "description": "The print size to set"}}, "required": ["size"],
                              "additionalProperties": False},
                input_schema_description='{ "size": one of "Normal print size", "Small print size", "Tiny print size"}'
            ),
            Action(
                name="print",
                title="Print",
                description="Presses the print button in the print dialog.",
                examples=[
                    Example(phrase="print"),
                    Example(phrase="print it"),
                    Example(phrase="print photo"),
                    Example(phrase="print picture"),
                    Example(phrase="i want a print"),
                    Example(phrase="i want to print"),
                    Example(phrase="let's print")
                ],
                next_state=ScopeNames.PRINT_DIALOG
            )
        ]
    ),
    ScopeNames.SHARE_SCREEN: ScopeInfo(
        name=ScopeNames.SHARE_SCREEN.value,
        description="The final screen for a new capture, offering printing and sharing options.",
        actions=[
            Action(
                name="retake",
                title="Retake Photo",
                description="Retake the current photo.",
                examples=[
                    Example(phrase="retake"),
                    Example(phrase="take again"),
                    Example(phrase="try again"),
                    Example(phrase="do it again")
                ],
                next_state=ScopeNames.COLLAGE_MAKER_SCREEN
            ),
            Action(
                name="share_with_qr_code_dialog",
                title="Share with QR Code",
                description="Upload the photo, generate a QR code and display it in a dialog to share the photo.",
                examples=[
                    Example(phrase="get qr code"),
                    Example(phrase="show qr code"),
                    Example(phrase="generate qr code"),
                    Example(phrase="share photo")
                ],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="open_print_dialog",
                title="Open Print Dialog",
                description="Open the print dialog where options can be selected and a print job can be submitted.",
                examples=[
                    Example(phrase="print"),
                    Example(phrase="print it"),
                    Example(phrase="print photo"),
                    Example(phrase="print picture"),
                    Example(phrase="i want a print"),
                    Example(phrase="i want to print"),
                    Example(phrase="let's print")
                ],
                next_state=ScopeNames.PRINT_DIALOG
            ),
            Action(
                name="continue",
                title="Continue",
                description="Proceed to the start screen.",
                examples=[
                    Example(phrase="continue"),
                    Example(phrase="next"),
                    Example(phrase="go on"),
                    Example(phrase="proceed"),
                    Example(phrase="keep going"),
                    Example(phrase="done"),
                    Example(phrase="finished")
                ],
                next_state=ScopeNames.START_SCREEN
            )
        ]
    ),
    ScopeNames.LANGUAGE_DIALOG: ScopeInfo(
        name=ScopeNames.LANGUAGE_DIALOG.value,
        description="A pop-up dialog where the user can change the application's language locale.",
        actions=[
            Action(
                name="set_language",
                title='Set Language',
                description='Change the application language to the chosen one for this session.',
                examples=[
                    Example(phrase="select English", arguments={"language_code": "en"}),
                    Example(phrase="use English", arguments={"language_code": "en"}),
                    Example(phrase="set language to English", arguments={"language_code": "en"}),
                    Example(phrase="change language to English", arguments={"language_code": "en"}),
                    Example(phrase="switch language to English", arguments={"language_code": "en"}),
                    Example(phrase="i want to use English", arguments={"language_code": "en"}),
                    Example(phrase="select Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="use Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="set language to Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="change language to Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="switch language to Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="i want to use Nederlands", arguments={"language_code": "nl"}),
                    Example(phrase="select Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="use Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="set language to Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="change language to Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="switch language to Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="i want to use Deutsch", arguments={"language_code": "de"}),
                    Example(phrase="select Français", arguments={"language_code": "fr"}),
                    Example(phrase="use Français", arguments={"language_code": "fr"}),
                    Example(phrase="set language to Français", arguments={"language_code": "fr"}),
                    Example(phrase="change language to Français", arguments={"language_code": "fr"}),
                    Example(phrase="switch language to Français", arguments={"language_code": "fr"}),
                    Example(phrase="i want to use Français", arguments={"language_code": "fr"})
                ],
                next_state=ScopeNames.NAVIGATION_SCREEN,
                input_schema={"type": "object", "properties": {"language_code": {"enum": ["en", "nl", "de", "fr"],
                                                                                 "description": "The ISO 639-1 code for the language to set"}},
                              "required": ["language_code"], "additionalProperties": False},
                input_schema_description='{ "language_code": one of "en", "nl", "de", "fr" } }'
            ),
            Action(
                name="dismiss",
                title='Dismiss',
                description='Close the language selection dialog without changing the language.',
                examples=[
                    Example(phrase="cancel"),
                    Example(phrase="stop"),
                    Example(phrase="abort"),
                    Example(phrase="never mind"),
                    Example(phrase="forget it"),
                    Example(phrase="close"),
                    Example(phrase="dismiss"),
                    Example(phrase="exit")
                ],
                next_state=ScopeNames.NAVIGATION_SCREEN
            )
        ]
    ),
    ScopeNames.QR_DIALOG: ScopeInfo(
        name=ScopeNames.QR_DIALOG.value,
        description="A dialog displaying a QR code for the user to download their image.",
        actions=[
            Action(
                name="redo_upload",
                title='Redo Upload',
                description="Start the upload process again to get a new QR code",
                examples=[
                    Example(phrase="redo upload"),
                    Example(phrase="upload again"),
                    Example(phrase="upload another one"),
                    Example(phrase="get me a new QR code")
                ],
                next_state=ScopeNames.QR_DIALOG
            ),
            Action(
                name="close",
                title='Close',
                description='Close the QR sharing dialog.',
                examples=[
                    Example(phrase="cancel"),
                    Example(phrase="stop"),
                    Example(phrase="abort"),
                    Example(phrase="never mind"),
                    Example(phrase="forget it"),
                    Example(phrase="close"),
                    Example(phrase="dismiss"),
                    Example(phrase="exit")
                ],
                next_state=ScopeNames.SHARE_SCREEN
            )
        ]
    )
}
