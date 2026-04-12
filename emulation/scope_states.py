from enum import StrEnum


class ScopeNames(StrEnum):
    START_SCREEN = "Start Screen"
    NAVIGATION_SCREEN = "Navigation Screen"
    COLLAGE_MAKER_SCREEN = "Collage Maker Screen"
    GALLERY = "Gallery"
    PHOTO_DETAILS_SCREEN = "Photo Details Screen"
    PRINT_DIALOG = "Print Dialog"
    SHARE_SCREEN = "Share Screen"
    LANGUAGE_DIALOG = "Language Dialog"


SCOPE_STATES = {
    ScopeNames.START_SCREEN: [
        {
            "name": "start",
            "title": "Start",
            "description": "Begin the photo booth experience.",
            "examples": ["start", "begin", "let's go", "proceed", "continue"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.NAVIGATION_SCREEN
        }
    ],
    ScopeNames.NAVIGATION_SCREEN: [
        {
            "name": "single_photo",
            "title": "Single Photo",
            "description": "Take a single photo.",
            "examples": ["single", "single capture", "single photo", "single picture", "take a photo"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.SHARE_SCREEN
        },
        {
            "name": "collage",
            "title": "Collage",
            "description": "Shoot multiple photos and create a collage from them.",
            "examples": ["collage", "collage capture", "collage photo", "collage picture", "take a collage"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.COLLAGE_MAKER_SCREEN
        },
        {
            "name": "gallery",
            "title": "Gallery",
            "description": "View the previously captured photos.",
            "examples": ["gallery", "view gallery", "see photos", "browse images"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.GALLERY
        },
        {
            "name": "open_language_dialog",
            "title": "Language",
            "description": "Open the language selection dialog.",
            "examples": ["language", "change language", "select language", "set language", "open language settings"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.LANGUAGE_DIALOG
        }
    ],
    ScopeNames.COLLAGE_MAKER_SCREEN: [
        {
            "name": "select_pictures",
            "title": "Select Pictures",
            "description": "Choose pictures to include in the collage.",
            "examples": ["select picture {selected}, {selected} and {selected}",
                         "select picture {selected} and {second}", "select picture {selected}",
                         "select the {selected} picture", "select the {selected} and {selected} picture",
                         "select the {selected}, {selected}, and {selected} picture"],
            "inputSchema": "{ \"type\": \"object\", \"properties\": { \"selected\": { \"type\": \"array\", \"items\": { \"type\": \"integer\", \"minimum\": 1, \"maximum\": 4 }, \"minItems\": 0, \"maxItems\": 4 }}, \"description\": \"The indices of the selected pictures, 1-indexed\", \"required\": [\"selected\"], \"additionalProperties\": false }",
            "next_state": ScopeNames.COLLAGE_MAKER_SCREEN
        },
        {
            "name": "continue",
            "title": "Continue",
            "description": "Proceed to the share screen.",
            "examples": ["continue", "next", "go on", "proceed", "keep going", "done", "finished"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.SHARE_SCREEN
        },
        {
            "name": "select_all_pictures",
            "title": "Select All Pictures",
            "description": "Select all captured pictures",
            "examples": ["select all pictures", "select all photos", "select all images", "select all",
                         "all of them", "all pictures", "use all pictures"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.COLLAGE_MAKER_SCREEN
        }
    ],
    ScopeNames.GALLERY: [
        {
            "name": "open_latest_picture",
            "title": "Open Latest Picture",
            "description": "View the most recently captured picture.",
            "examples": ["latest", "most recent", "last photo", "last picture", "open latest"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.PHOTO_DETAILS_SCREEN
        },
        {
            "name": "back",
            "title": "Back",
            "description": "Return to the previous screen.",
            "examples": ["back", "previous", "go back", "return", "previous screen"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.NAVIGATION_SCREEN
        }
    ],
    ScopeNames.PHOTO_DETAILS_SCREEN: [
        {
            "name": "back",
            "title": "Back",
            "description": "Return to the gallery screen.",
            "examples": ["back", "previous", "go back", "return", "previous screen"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.GALLERY
        },
        {
            "name": "get_qr",
            "title": "Get QR Code",
            "description": "Generate a QR code for sharing the photo.",
            "examples": ["get qr code", "show qr code", "generate qr code", "share photo"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.PHOTO_DETAILS_SCREEN
        },
        {
            "name": "open_print_dialog",
            "title": "Print",
            "description": "Open the print dialog.",
            "examples": ["print", "print it", "print photo", "print picture", "i want a print", "i want to print",
                         "let's print"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.PRINT_DIALOG
        }
    ],
    ScopeNames.PRINT_DIALOG: [
        {
            "name": "cancel",
            "title": "Cancel",
            "description": "Presses the cancel button in the print dialog.",
            "examples": ["cancel", "stop", "abort", "never mind", "forget it"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }"
        },
        {
            "name": "set_print_count",
            "title": "Set Print Count",
            "description": "Sets the number of copies to print.",
            "examples": ["print five pictures", "set three copies", "two times"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }"
        },
        {
            "name": "print",
            "title": "Print",
            "description": "Presses the print button in the print dialog.",
            "examples": ["print", "print it", "print photo", "print picture", "i want a print", "i want to print",
                         "let's print"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }"
        }
    ],
    ScopeNames.SHARE_SCREEN: [
        {
            "name": "retake",
            "title": "Retake Photo",
            "description": "Retake the current photo.",
            "examples": ["retake", "take again", "try again", "do it again"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.COLLAGE_MAKER_SCREEN
        },
        {
            "name": "get_qr",
            "title": "Get QR Code",
            "description": "Generate a QR code for sharing the photo.",
            "examples": ["get qr code", "show qr code", "generate qr code", "share photo"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.SHARE_SCREEN
        },
        {
            "name": "print",
            "title": "Print Photo",
            "description": "Open the print dialog.",
            "examples": ["print", "print it", "print photo", "print picture", "i want a print", "i want to print",
                         "let's print"], "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.PRINT_DIALOG
        },
        {
            "name": "continue",
            "title": "Continue",
            "description": "Proceed to the start screen.",
            "examples": ["continue", "next", "go on", "proceed", "keep going", "done", "finished"],
            "inputSchema": "{ \"type\": \"object\", \"additionalProperties\": false }",
            "next_state": ScopeNames.START_SCREEN
        }
    ],
    ScopeNames.LANGUAGE_DIALOG: [
        {
            "name": "set_language",
            "title": 'Set Language',
            "description": 'Change the application language to the chosen one for this session.',
            "examples": ['set language to {language_code}', 'set language to {language_code}', 'set language to {language_code}'],
            "inputSchema": '{ "type": "object", "properties": { "language_code": { "type": "string", "description": "The ISO 639-1 code for the language to set" } }, "required": ["language_code"], "additionalProperties": false }',
            "next_state": ScopeNames.NAVIGATION_SCREEN
        }
    ]
}
