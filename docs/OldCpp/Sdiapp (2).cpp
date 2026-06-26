//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
USEFORM("SDIMain.cpp", SDIAppForm);
USEFORM("Unit1.cpp", OKBottomDlg);
USEFORM("About.cpp", AboutBox);
USEFORM("Unit10.cpp", Form10);
USEFORM("Unit11.cpp", Form11);
USEFORM("Unit12.cpp", Form12);
USEFORM("Unit14.cpp", Form14);
USEFORM("Unit2.cpp", Form2);
USEFORM("Unit5.cpp", Form5);
USEFORM("Unit6.cpp", Form6);
USEFORM("Unit9.cpp", Form9);
USEFORM("Unit4.cpp", Form4);
USEFORM("Unit15.cpp", Form15);
USEFORM("Unit16.cpp", Form16);
USEFORM("Unit18.cpp", Form18);
USEFORM("Unit19.cpp", Form19);
USEFORM("Unit20.cpp", Form20);
USEFORM("Unit21.cpp", Form21);
USEFORM("Unit22.cpp", Form22);
USEFORM("Unit23.cpp", Form23);
USEFORM("Unit3.cpp", Form3);
USEFORM("Unit13.cpp", Form13);
USEFORM("Unit25.cpp", Form25);
USEFORM("Unit27.cpp", Form27);
USEFORM("Unit28.cpp", Form28);
USEFORM("Unit77.cpp", Form7);
//---------------------------------------------------------------------------
WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int)
{
    try
    {
        Application->Initialize();
        Application->Title = "LIBS";
                 Application->CreateForm(__classid(TSDIAppForm), &SDIAppForm);
                 Application->CreateForm(__classid(TForm15), &Form15);
                 Application->CreateForm(__classid(TForm10), &Form10);
                 Application->CreateForm(__classid(TForm11), &Form11);
                 Application->CreateForm(__classid(TForm12), &Form12);
                 Application->CreateForm(__classid(TForm2), &Form2);
                 Application->CreateForm(__classid(TForm5), &Form5);
                 Application->CreateForm(__classid(TForm9), &Form9);
                 Application->CreateForm(__classid(TForm4), &Form4);
                 Application->CreateForm(__classid(TOKBottomDlg), &OKBottomDlg);
                 Application->CreateForm(__classid(TForm6), &Form6);
                 Application->CreateForm(__classid(TForm14), &Form14);
                 Application->CreateForm(__classid(TAboutBox), &AboutBox);
                 Application->CreateForm(__classid(TForm16), &Form16);
                 Application->CreateForm(__classid(TForm18), &Form18);
                 Application->CreateForm(__classid(TForm19), &Form19);
                 Application->CreateForm(__classid(TForm20), &Form20);
                 Application->CreateForm(__classid(TForm21), &Form21);
                 Application->CreateForm(__classid(TForm22), &Form22);
                 Application->CreateForm(__classid(TForm23), &Form23);
                 Application->CreateForm(__classid(TForm3), &Form3);
                 Application->CreateForm(__classid(TForm13), &Form13);
                 Application->CreateForm(__classid(TForm25), &Form25);
                 Application->CreateForm(__classid(TForm27), &Form27);
                 Application->CreateForm(__classid(TForm28), &Form28);
                 Application->CreateForm(__classid(TForm7), &Form7);
                 Application->Run();
                     }
    catch (Exception &exception)
    {
        Application->ShowException(&exception);
    }
    return 0;
}
//---------------------------------------------------------------------------

