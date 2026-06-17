# Kiwoom API Discovery Summary

## Environment

- PyQt5.QAxContainer available: `True`
- Candidate ProgIDs tested: `5`

## Detected ProgIDs

- `KHOPENAPI.KHOpenAPICtrl.1`
- `KFOPENAPI.KFOpenAPICtrl.1`
- `KFOpenAPI.KFOpenAPICtrl.1`

## Likely Overseas Futures ProgID

- `KFOPENAPI.KFOpenAPICtrl.1`

HeroMoonG / overseas futures environments may use a different COM control from domestic stock OpenAPI.
The next integration step should follow the detected overseas futures-like ProgID rather than assuming domestic compatibility.

## Candidate Notes

- `KHOPENAPI.KHOpenAPICtrl.1` registry=`True` created=`True` CommConnect=`yes` GetConnectState=`yes` SetRealReg=`yes` SetRealRemove=`yes` error=``
- `KFOPENAPI.KFOpenAPICtrl.1` registry=`True` created=`True` CommConnect=`unknown` GetConnectState=`yes` SetRealReg=`unknown` SetRealRemove=`unknown` error=``
- `KFOpenAPI.KFOpenAPICtrl.1` registry=`True` created=`True` CommConnect=`unknown` GetConnectState=`yes` SetRealReg=`unknown` SetRealRemove=`unknown` error=``
- `KHOPENAPI.KHOpenAPICtrl` registry=`False` created=`False` CommConnect=`unavailable` GetConnectState=`unavailable` SetRealReg=`unavailable` SetRealRemove=`unavailable` error=`QAxWidget is null after creation`
- `KFOPENAPI.KFOpenAPICtrl` registry=`False` created=`False` CommConnect=`unavailable` GetConnectState=`unavailable` SetRealReg=`unavailable` SetRealRemove=`unavailable` error=`QAxWidget is null after creation`
