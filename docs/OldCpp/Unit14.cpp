//---------------------------------------------------------------------------
#include <vcl.h>
#include "SDIMain.h"
#include "Math.h"
#include "Windows.h"
#include "Unit1.h"
#include "Unit6.h"
#include "Unit14.h"
#include "Unit15.h"
#include "Unit18.h"
#pragma hdrstop
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm14 *Form14;
//---------------------------------------------------------------------------
__fastcall TForm14::TForm14(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm14::FormCreate(TObject *Sender)
{
void readini();
 readini();
 Form14->StringGrid1->ColWidths[0]=55;
 Form14->StringGrid1->ColWidths[1]=200;
 Form14->StringGrid1->ColWidths[2]=200;
 Form14->StringGrid1->Cells[1][0]="Value";
    Form14->StringGrid1->Cells[2][0]="Error";
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Button2Click(TObject *Sender)
{
void condizioni();
Form14->Button7->Visible=true;
Form14->Button7->Enabled=false;
Form14->Button9->Visible=true;
Form14->Button9->Enabled=false;

SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
if((fabs(atof(AnsiString(Form14->Edit6->Text).c_str()))!= SDIAppForm->Series4->XValues->Value[firstlin] && fabs(atof(AnsiString(Form14->Edit6->Text).c_str()))!=fabs(Form6->Table1->FieldByName("fitwavelen")->AsFloat)))
{
 condizioni();
}
void manfit();
  SDIAppForm->Edit7->Text="0";
  Form14->ProgressBar1->Position=0;
   Form14->Edit2->Text="Starting Fit....";
manfit();
Close();
Show();
}
//---------------------------------------------------------------------------


void __fastcall TForm14::Button3Click(TObject *Sender)
{
 Form14->Edit2->Text="";
  SDIAppForm->Edit7->Text="1";
Close();
Show();
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Button1Click(TObject *Sender)
{
  Form14->Edit2->Text="";
  SDIAppForm->Edit7->Text="0";
    Form14->ProgressBar1->Position=0;
     
 /*
   SDIAppForm->Edit12->Text=SDIAppForm->Edit10->Text;
      SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;
 */
 Form14->Close();
  Form14->Show();
return;
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Button4Click(TObject *Sender)
{
void autofit(float jmin, float jmax, int j);
void condizioni();

 Form14->Edit2->Text="Moving to next region";
   Form14->ProgressBar1->Position=0;
  SDIAppForm->Edit7->Text="0";
  float jmin = 0;
   float jmax = Form6->Table1->RecordCount;

 int j = atoi(AnsiString(SDIAppForm->Edit12->Text).c_str());

  if (SDIAppForm->Series4->LastValueIndex+1 < jmax)
	{
   j=SDIAppForm->Series4->LastValueIndex+1;
	  SDIAppForm->Edit12->Text=j;
	   autofit(jmin,jmax,j);

	 }

			Close();
			Show();
		condizioni();
			return;

}
//---------------------------------------------------------------------------


void __fastcall TForm14::Button5Click(TObject *Sender)
{
 SDIAppForm->Edit7->Text="-1";
   Form14->ProgressBar1->Position=0;
 Close();
 Show();  
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Button6Click(TObject *Sender)
{
void autofit(float jmin, float jmax, int j);
void condizioni();

 Form14->Edit2->Text="Moving to previous region";
   Form14->ProgressBar1->Position=0;
  SDIAppForm->Edit7->Text="0";
  float jmin = 0;
   float jmax = Form6->Table1->RecordCount;

 int j = atoi(AnsiString(SDIAppForm->Edit12->Text).c_str());

  if (SDIAppForm->Series4->FirstValueIndex > jmin)
	{
	j=SDIAppForm->Series4->FirstValueIndex-1;
	  SDIAppForm->Edit12->Text=j;
	   autofit(jmin,jmax,j);

	 }
			Close();
			Show();
		condizioni();
			return;
}
//---------------------------------------------------------------------------






void __fastcall TForm14::Chart1Click(TObject *Sender)
{
if (Form14->Series2->Active==False) Form14->Series2->Active=True;
else
 Form14->Series2->Active=False;
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Button7Click(TObject *Sender)
{
if (Form14->Width==Form14->Panel1->Width) Form14->Width=Form14->Panel2->Width;
else {Form14->Width=Form14->Panel1->Width;

}
}
//---------------------------------------------------------------------------

  void condizioni()
  {

  float *vector(long nl,long nh);
  float *a;
  int k;

  /* cancello la tabella */

  Form14->Edit6->Text="";Form14->Edit7->Text="";Form14->Edit8->Text="";Form14->Edit9->Text="";Form14->Edit18->Text="";
  Form14->Edit10->Text="";Form14->Edit11->Text="";Form14->Edit12->Text="";Form14->Edit13->Text="";Form14->Edit19->Text="";
  Form14->Edit14->Text="";Form14->Edit15->Text="";Form14->Edit16->Text="";Form14->Edit17->Text="";Form14->Edit20->Text="";
  Form14->Edit21->Text="";Form14->Edit22->Text="";Form14->Edit23->Text="";Form14->Edit24->Text="";Form14->Edit25->Text="";
  Form14->Edit26->Text="";Form14->Edit27->Text="";Form14->Edit28->Text="";Form14->Edit29->Text="";Form14->Edit30->Text="";
  Form14->Edit31->Text="";Form14->Edit32->Text="";Form14->Edit33->Text="";Form14->Edit34->Text="";Form14->Edit35->Text="";
  Form14->CheckBox6->Checked=false;Form14->CheckBox7->Checked=false;Form14->CheckBox8->Checked=false;Form14->CheckBox9->Checked=false;Form14->CheckBox10->Checked=false;
  Form14->CheckBox11->Checked=false;Form14->CheckBox12->Checked=false;Form14->CheckBox13->Checked=false;Form14->CheckBox14->Checked=false;Form14->CheckBox15->Checked=false;
  Form14->CheckBox16->Checked=false;Form14->CheckBox17->Checked=false;Form14->CheckBox18->Checked=false;Form14->CheckBox19->Checked=false;Form14->CheckBox25->Checked=false;
  Form14->CheckBox20->Checked=false;Form14->CheckBox21->Checked=false;Form14->CheckBox22->Checked=false;Form14->CheckBox23->Checked=false;Form14->CheckBox24->Checked=false;
  Form14->CheckBox26->Checked=false;Form14->CheckBox27->Checked=false;Form14->CheckBox28->Checked=false;Form14->CheckBox29->Checked=false;Form14->CheckBox30->Checked=false;
  Form14->CheckBox31->Checked=false;Form14->CheckBox32->Checked=false;Form14->CheckBox33->Checked=false;Form14->CheckBox34->Checked=false;Form14->CheckBox35->Checked=false;
  Form14->Edit6->Color=clMoneyGreen;Form14->Edit7->Color=clMoneyGreen;Form14->Edit8->Color=clMoneyGreen;Form14->Edit9->Color=clMoneyGreen;Form14->Edit10->Color=clMoneyGreen;
  Form14->Edit11->Color=clMoneyGreen;Form14->Edit12->Color=clMoneyGreen;Form14->Edit13->Color=clMoneyGreen;Form14->Edit14->Color=clMoneyGreen;Form14->Edit15->Color=clMoneyGreen;
  Form14->Edit16->Color=clMoneyGreen;Form14->Edit17->Color=clMoneyGreen;Form14->Edit18->Color=clMoneyGreen;Form14->Edit19->Color=clMoneyGreen;Form14->Edit20->Color=clMoneyGreen;
  Form14->Edit21->Color=clMoneyGreen;Form14->Edit22->Color=clMoneyGreen;Form14->Edit23->Color=clMoneyGreen;Form14->Edit24->Color=clMoneyGreen;Form14->Edit25->Color=clMoneyGreen;
  Form14->Edit26->Color=clMoneyGreen;Form14->Edit27->Color=clMoneyGreen;Form14->Edit28->Color=clMoneyGreen;Form14->Edit29->Color=clMoneyGreen;Form14->Edit30->Color=clMoneyGreen;
  Form14->Edit31->Color=clMoneyGreen;Form14->Edit32->Color=clMoneyGreen;Form14->Edit33->Color=clMoneyGreen;Form14->Edit34->Color=clMoneyGreen;Form14->Edit35->Color=clMoneyGreen;






  /* riempio la tabella */

  
  SDIAppForm->Series4->Active=true;


  int group = (SDIAppForm->Series4->LastValueIndex - SDIAppForm->Series4->FirstValueIndex) +1;

   if (group > 10)
   {
   Form14->Show();
   Form14->Edit2->Text="Too many lines for fitting (> 10)";

     return;
   }

   if (group < 1)
   {
   Form14->Show();
   Form14->Edit2->Text="No lines for fitting";

     return;
   }

   int fix[3];
   int na=group*3;
        a=vector(0,na);
   int  firstlin=SDIAppForm->Series4->FirstValueIndex;
        /* inizio ciclo sulle righe*/

   for (k=0;k<group;k++)
  {



  /* lunghezze d'onda */

      Form6->Table1->RecNo=firstlin+1+k;
	  if (Form6->Table1->FieldByName("wavelen")->AsFloat !=0.0)
      {
	   a[k*3]= fabs(Form6->Table1->FieldByName("wavelen")->AsFloat);
       if (Form6->Table1->FieldByName("wavelen")->AsFloat<0)
       {
       fix[0]=1;
       }
      else      {
                fix[0]=0;
                }
      }
      else      {
                a[k*3]= SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k];
                fix[0]=0;
                }

     /* larghezze gaussiane */

      if (Form6->Table1->FieldByName("wg")->AsFloat!=0)
      {
 //      a[1+k*3]= fabs(Form6->Table1->FieldByName("wg")->AsFloat);
		   a[1+k*3]= atof(AnsiString(OKBottomDlg->Edit14->Text).c_str());
	   if (Form6->Table1->FieldByName("wg")->AsFloat<0)
       {
       fix[1]=1;
       }
      else      {
                fix[1]=0;
                }
      }
      else      {
				a[1+k*3]= atof(AnsiString(OKBottomDlg->Edit14->Text).c_str());
                fix[1]=0;
                }

      /* larghezze gaussiane */


       if (Form6->Table1->FieldByName("wl")->AsFloat!=0)
      {
 //      a[2+k*3]= fabs(Form6->Table1->FieldByName("wl")->AsFloat);
	   a[2+k*3]= atof(AnsiString(OKBottomDlg->Edit15->Text).c_str());
       if (Form6->Table1->FieldByName("wl")->AsFloat<0)
       {
       fix[2]=1;
       }
      else      {
                fix[2]=0;
                }
      }
	  else      {
				a[2+k*3]= atof(AnsiString(OKBottomDlg->Edit15->Text).c_str());
                fix[2]=0;
                }

  switch(k)
                {
                case 0:
                Form14->Edit6->Text=a[k*3]; Form14->Edit7->Text=a[1+k*3]; Form14->Edit8->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox6->Checked=true; Form14->Edit6->Color=clRed;}else{Form14->CheckBox6->Checked=false; Form14->Edit6->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox7->Checked=true; Form14->Edit7->Color=clRed;}else{Form14->CheckBox7->Checked=false; Form14->Edit7->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox8->Checked=true; Form14->Edit8->Color=clRed;}else{Form14->CheckBox8->Checked=false; Form14->Edit8->Color=clMoneyGreen;}break;
                case 1:
                Form14->Edit9->Text=a[k*3]; Form14->Edit10->Text=a[1+k*3]; Form14->Edit11->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox9->Checked=true; Form14->Edit9->Color=clRed;}else{Form14->CheckBox9->Checked=false; Form14->Edit9->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox10->Checked=true; Form14->Edit10->Color=clRed;}else{Form14->CheckBox10->Checked=false; Form14->Edit10->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox11->Checked=true; Form14->Edit11->Color=clRed;}else{Form14->CheckBox11->Checked=false; Form14->Edit11->Color=clMoneyGreen;}break;
                case 2:
                Form14->Edit12->Text=a[k*3]; Form14->Edit13->Text=a[1+k*3]; Form14->Edit14->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox12->Checked=true; Form14->Edit12->Color=clRed;}else{Form14->CheckBox12->Checked=false; Form14->Edit12->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox13->Checked=true; Form14->Edit13->Color=clRed;}else{Form14->CheckBox13->Checked=false; Form14->Edit13->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox14->Checked=true; Form14->Edit14->Color=clRed;}else{Form14->CheckBox14->Checked=false; Form14->Edit14->Color=clMoneyGreen;}break;
                case 3:
                Form14->Edit15->Text=a[k*3]; Form14->Edit16->Text=a[1+k*3]; Form14->Edit17->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox15->Checked=true; Form14->Edit15->Color=clRed;}else{Form14->CheckBox15->Checked=false; Form14->Edit15->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox16->Checked=true; Form14->Edit16->Color=clRed;}else{Form14->CheckBox16->Checked=false; Form14->Edit16->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox17->Checked=true; Form14->Edit17->Color=clRed;}else{Form14->CheckBox17->Checked=false; Form14->Edit17->Color=clMoneyGreen;}break;
                case 4:
                Form14->Edit18->Text=a[k*3]; Form14->Edit19->Text=a[1+k*3]; Form14->Edit20->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox18->Checked=true; Form14->Edit18->Color=clRed;}else{Form14->CheckBox18->Checked=false; Form14->Edit18->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox19->Checked=true; Form14->Edit19->Color=clRed;}else{Form14->CheckBox19->Checked=false; Form14->Edit19->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox20->Checked=true; Form14->Edit20->Color=clRed;}else{Form14->CheckBox20->Checked=false; Form14->Edit20->Color=clMoneyGreen;}break;
                case 5:
                Form14->Edit21->Text=a[k*3]; Form14->Edit22->Text=a[1+k*3]; Form14->Edit23->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox21->Checked=true; Form14->Edit21->Color=clRed;}else{Form14->CheckBox21->Checked=false; Form14->Edit21->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox22->Checked=true; Form14->Edit22->Color=clRed;}else{Form14->CheckBox22->Checked=false; Form14->Edit22->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox23->Checked=true; Form14->Edit23->Color=clRed;}else{Form14->CheckBox23->Checked=false; Form14->Edit23->Color=clMoneyGreen;}break;
                case 6:
                Form14->Edit24->Text=a[k*3]; Form14->Edit25->Text=a[1+k*3]; Form14->Edit26->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox24->Checked=true; Form14->Edit24->Color=clRed;}else{Form14->CheckBox24->Checked=false; Form14->Edit24->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox25->Checked=true; Form14->Edit25->Color=clRed;}else{Form14->CheckBox25->Checked=false; Form14->Edit25->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox26->Checked=true; Form14->Edit26->Color=clRed;}else{Form14->CheckBox26->Checked=false; Form14->Edit26->Color=clMoneyGreen;}break;
                case 7:
                Form14->Edit27->Text=a[k*3]; Form14->Edit28->Text=a[1+k*3]; Form14->Edit29->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox27->Checked=true; Form14->Edit27->Color=clRed;}else{Form14->CheckBox27->Checked=false; Form14->Edit27->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox28->Checked=true; Form14->Edit28->Color=clRed;}else{Form14->CheckBox28->Checked=false; Form14->Edit28->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox29->Checked=true; Form14->Edit29->Color=clRed;}else{Form14->CheckBox29->Checked=false; Form14->Edit29->Color=clMoneyGreen;}break;
                case 8:
                Form14->Edit30->Text=a[k*3]; Form14->Edit31->Text=a[1+k*3]; Form14->Edit31->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox30->Checked=true; Form14->Edit30->Color=clRed;}else{Form14->CheckBox30->Checked=false; Form14->Edit30->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox31->Checked=true; Form14->Edit31->Color=clRed;}else{Form14->CheckBox31->Checked=false; Form14->Edit31->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox32->Checked=true; Form14->Edit32->Color=clRed;}else{Form14->CheckBox32->Checked=false; Form14->Edit32->Color=clMoneyGreen;}break;
                case 9:
                Form14->Edit33->Text=a[k*3]; Form14->Edit34->Text=a[1+k*3]; Form14->Edit35->Text=a[2+k*3];
                if (fix[0]==1) {Form14->CheckBox33->Checked=true; Form14->Edit33->Color=clRed;}else{Form14->CheckBox33->Checked=false; Form14->Edit33->Color=clMoneyGreen;}
                if (fix[1]==1) {Form14->CheckBox34->Checked=true; Form14->Edit34->Color=clRed;}else{Form14->CheckBox34->Checked=false; Form14->Edit34->Color=clMoneyGreen;}
                if (fix[2]==1) {Form14->CheckBox35->Checked=true; Form14->Edit35->Color=clRed;}else{Form14->CheckBox35->Checked=false; Form14->Edit35->Color=clMoneyGreen;}break;
                }
  }
  }
//---------------------------------------------------------------------------
  void __fastcall TForm14::Button9Click(TObject *Sender)
{
void condizioni();
condizioni();
}
//---------------------------------------------------------------------------



void __fastcall TForm14::CheckBox6MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox6->State==cbChecked)
{Edit6->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit6->Text).c_str());
 }
 else
 {Edit6->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit6->Text).c_str());
 }
 Form6->Table1->Post();
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox9MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox9->State==cbChecked)
{Edit9->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit9->Text).c_str());
 }
 else
 {Edit9->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit9->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox12MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox12->State==cbChecked)
{Edit12->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit12->Text).c_str());
 }
 else
 {Edit12->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit12->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox15MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox15->State==cbChecked)
{Edit15->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit15->Text).c_str());
 }
 else
 {Edit15->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit15->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox18MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox18->State==cbChecked)
{Edit18->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit18->Text).c_str());
 }
 else
 {Edit18->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit18->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox21MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox21->State==cbChecked)
{Edit21->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit21->Text).c_str());
 }
 else
 {Edit21->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit21->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox24MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox24->State==cbChecked)
{Edit24->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit24->Text).c_str());
 }
 else
 {Edit24->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit24->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox27MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox27->State==cbChecked)
{Edit27->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit27->Text).c_str());
 }
 else
 {Edit27->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit27->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox30MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox30->State==cbChecked)
{Edit30->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit30->Text).c_str());
 }
 else
 {Edit30->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit30->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox33MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox33->State==cbChecked)
{Edit33->Color=clRed;
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit33->Text).c_str());
 }
 else
 {Edit33->Color=clMoneyGreen;
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit33->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox7MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox7->State==cbChecked)
{Edit7->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit7->Text).c_str());
 }
 else
 {Edit7->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit7->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox10MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox10->State==cbChecked)
{Edit10->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit10->Text).c_str());
 }
 else
 {Edit10->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit10->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox13MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox13->State==cbChecked)
{Edit13->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit13->Text).c_str());
 }
 else
 {Edit13->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit13->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox16MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox16->State==cbChecked)
{Edit16->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit16->Text).c_str());
 }
 else
 {Edit16->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit16->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox19MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox19->State==cbChecked)
{Edit19->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit19->Text).c_str());
 }
 else
 {Edit19->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit19->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox22MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox22->State==cbChecked)
{Edit22->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit22->Text).c_str());
 }
 else
 {Edit22->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit22->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox25MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
 Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox25->State==cbChecked)
{Edit25->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit25->Text).c_str());
 }
 else
 {Edit25->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit25->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox28MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox28->State==cbChecked)
{Edit28->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit28->Text).c_str());
 }
 else
 {Edit28->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit28->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox31MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox31->State==cbChecked)
{Edit31->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit31->Text).c_str());
 }
 else
 {Edit31->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit31->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox34MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox34->State==cbChecked)
{Edit34->Color=clRed;
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit34->Text).c_str());
 }
 else
 {Edit34->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit34->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox8MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox8->State==cbChecked)
{Edit8->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit8->Text).c_str());
 }
 else
 {Edit8->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit8->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox11MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox11->State==cbChecked)
{Edit11->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit11->Text).c_str());
 }
 else
 {Edit11->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit11->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox14MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox14->State==cbChecked)
{Edit14->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit14->Text).c_str());
 }
 else
 {Edit14->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit14->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox17MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox17->State==cbChecked)
{Edit17->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit17->Text).c_str());
 }
 else
 {Edit17->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit17->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox20MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox20->State==cbChecked)
{Edit20->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit20->Text).c_str());
 }
 else
 {Edit20->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit20->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox23MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox23->State==cbChecked)
{Edit23->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit23->Text).c_str());
 }
 else
 {Edit23->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit23->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox26MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox26->State==cbChecked)
{Edit26->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit26->Text).c_str());
 }
 else
 {Edit26->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit26->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox29MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox29->State==cbChecked)
{Edit29->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit29->Text).c_str());
 }
 else
 {Edit29->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit29->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox32MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox32->State==cbChecked)
{Edit32->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit32->Text).c_str());
 }
 else
 {Edit32->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit32->Text).c_str());
 }
 Form6->Table1->Post();        
}
//---------------------------------------------------------------------------

void __fastcall TForm14::CheckBox35MouseUp(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox35->State==cbChecked)
{Edit35->Color=clRed;
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit35->Text).c_str());
 }
 else
 {Edit35->Color=clMoneyGreen;
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit35->Text).c_str());
 }
 Form6->Table1->Post();
}
//---------------------------------------------------------------------------


void __fastcall TForm14::Edit6KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox6->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit6->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit6->Text).c_str());
 }
 Form6->Table1->Post();

}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit7KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox7->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit7->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit7->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------



void __fastcall TForm14::Edit8KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox8->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit8->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit8->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit9KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+1;
Form6->Table1->Edit();

if (CheckBox9->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit9->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit9->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit12KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox12->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit12->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit12->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit15KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox15->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit15->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit15->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------


void __fastcall TForm14::Edit18KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox18->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit18->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit18->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit21KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox21->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit21->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit21->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit24KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox24->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit24->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit24->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit27KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox27->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit27->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit27->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------


void __fastcall TForm14::Edit30KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox30->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit30->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit30->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit33KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox33->State==cbChecked)
{
 Form6->Table1->FieldValues["fitwavelen"]=-atof(AnsiString(Form14->Edit33->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["fitwavelen"]=atof(AnsiString(Form14->Edit33->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit10KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox10->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit10->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit10->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit13KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox13->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit13->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit13->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit16KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox16->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit16->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit16->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit19KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox19->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit19->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit19->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit22KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox22->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit22->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit22->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit25KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox25->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit25->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit25->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit28KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox28->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit28->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit28->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit31KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox31->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit31->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit31->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit34KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox34->State==cbChecked)
{
 Form6->Table1->FieldValues["wg"]=-atof(AnsiString(Form14->Edit34->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wg"]=atof(AnsiString(Form14->Edit34->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit11KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+2;
Form6->Table1->Edit();

if (CheckBox11->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit11->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit11->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit14KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+3;
Form6->Table1->Edit();

if (CheckBox14->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit14->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit14->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit17KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+4;
Form6->Table1->Edit();

if (CheckBox17->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit17->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit17->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit20KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+5;
Form6->Table1->Edit();

if (CheckBox20->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit20->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit20->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit23KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+6;
Form6->Table1->Edit();

if (CheckBox23->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit23->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit23->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit26KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+7;
Form6->Table1->Edit();

if (CheckBox26->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit26->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit26->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit29KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+8;
Form6->Table1->Edit();

if (CheckBox29->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit29->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit29->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit32KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+9;
Form6->Table1->Edit();

if (CheckBox32->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit32->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit32->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm14::Edit35KeyPress(TObject *Sender, char &Key)
{
if (Key==VK_RETURN){

Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
int  firstlin=SDIAppForm->Series4->FirstValueIndex;
Form6->Table1->RecNo=firstlin+10;
Form6->Table1->Edit();

if (CheckBox35->State==cbChecked)
{
 Form6->Table1->FieldValues["wl"]=-atof(AnsiString(Form14->Edit35->Text).c_str());
 }
 else
 {
  Form6->Table1->FieldValues["wl"]=atof(AnsiString(Form14->Edit35->Text).c_str());
 }
 Form6->Table1->Post();
}
}
//---------------------------------------------------------------------------



void __fastcall TForm14::Button8Click(TObject *Sender)
{
Form18->Show();
}
//---------------------------------------------------------------------------

