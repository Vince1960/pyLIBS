//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
USERES("Test.res");
USEFORM("Unit17.cpp", Form17);
//---------------------------------------------------------------------------
WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int)
{
    try
    {
        Application->Initialize();
        Application->CreateForm(__classid(TForm17), &Form17);
        Application->Run();
    }
    catch (Exception &exception)
    {
        Application->ShowException(&exception);
    }
    return 0;
}
//---------------------------------------------------------------------------
