from dataclasses import dataclass

from scope_states import ScopeNames, SCOPE_STATES

@dataclass()
class ToolInvocation:
    name: str
    parameters: dict


@dataclass
class CommandExample:
    scope: ScopeNames
    transcript: str
    tool_invocations: list[ToolInvocation]


COMMAND_EXAMPLES: list[CommandExample] = [
    CommandExample(ScopeNames.START_SCREEN, "Start", [ToolInvocation("start", {})]),
    CommandExample(ScopeNames.START_SCREEN, "Plus to start. Okay, let's start.", [ToolInvocation("start", {})]),
    CommandExample(ScopeNames.NAVIGATION_SCREEN, "Take a picture.", [ToolInvocation("single_photo", {})]),
    CommandExample(ScopeNames.NAVIGATION_SCREEN, "Open the gallery for me.", [ToolInvocation("gallery", {})]),
    CommandExample(ScopeNames.NAVIGATION_SCREEN, "Maak een foto.", [ToolInvocation("single_photo", {})]),
    CommandExample(ScopeNames.NAVIGATION_SCREEN, "I want to I want to take collection", [ToolInvocation("collage", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Share photo.", [ToolInvocation("share_with_qr_code_dialog", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Get the qr code.", [ToolInvocation("share_with_qr_code_dialog", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Zo grappig. Upload the photo.", [ToolInvocation("share_with_qr_code_dialog", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Wat denkt hij dat er beschikbaar is? Welke dag is het vandaag?", []),
    CommandExample(ScopeNames.GALLERY, "Ga terug naar de start.", [ToolInvocation("back", {})]),
    CommandExample(ScopeNames.GALLERY, "Go back once more.", [ToolInvocation("back", {})]),
    CommandExample(ScopeNames.NAVIGATION_SCREEN, "Change the language.", [ToolInvocation("open_language_dialog", {})]),
    CommandExample(ScopeNames.LANGUAGE_DIALOG, "Set language to English.", [ToolInvocation("set_language", {"language_code": "en"})]),
    CommandExample(ScopeNames.LANGUAGE_DIALOG, "Ik wil Nederlands.", [ToolInvocation("set_language", {"language_code": "nl"})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "Select the first picture.", [ToolInvocation("select_pictures", {"selected": [1]})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "Select photos one two and three.", [ToolInvocation("select_pictures", {"selected": [1, 2, 3]})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "I want three pictures. I want four, one, two", [ToolInvocation("select_pictures", {"selected": [4, 1, 2]})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "Okay, select picture three, two, one", [ToolInvocation("select_pictures", {"selected": [3, 2, 1]})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "That's not a command. This is a command then. Give me all the pictures.", [ToolInvocation("select_all_pictures", {})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "Okay, one select picture", []),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "I said next.", [ToolInvocation("continue", {})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "Done.", [ToolInvocation("continue", {})]),
    CommandExample(ScopeNames.COLLAGE_MAKER_SCREEN, "What's up dog?", []),
    CommandExample(ScopeNames.SHARE_SCREEN, "But you can open the print dialogue.", [ToolInvocation("open_print_dialog", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Okay. Confetti! Get QR", [ToolInvocation("share_with_qr_code_dialog", {})]),
    CommandExample(ScopeNames.SHARE_SCREEN, "Print five times.", [ToolInvocation("open_print_dialog", {}), ToolInvocation("set_copies", {"copies": 5}), ToolInvocation("print", {})]),
]
