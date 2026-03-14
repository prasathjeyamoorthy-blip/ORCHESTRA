import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import main, validator, config
print('sig', main.process_documents.__code__.co_varnames, main.process_documents.__code__.co_argcount)
print('valid', validator.validate_documents.__code__.co_varnames, validator.validate_documents.__code__.co_argcount)
print('ration', hasattr(config,'RATION_CARD_PROMPT'), 'address', hasattr(config,'ADDRESS_PROOF_PROMPT'))
