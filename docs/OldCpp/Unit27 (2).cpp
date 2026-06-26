//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <dos.h>
#include <stdio.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit3.h"
#include "Unit4.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit7.h"
#include "Unit8.h"
#include "Unit9.h"
#include "Unit10.h"
#include "Unit15.h"
#include "Unit16.h"
#include "Unit23.h"
#include "Unit26.h"
#include <math.h>
#include <dir.h>
#define COLORE 12632150
#include "Unit27.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm27 *Form27;
//---------------------------------------------------------------------------
__fastcall TForm27::TForm27(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm27::Button2Click(TObject *Sender)
{
void replot();
Form9->RadioGroup1->ItemIndex=2;
Form9->Edit1->Text=Form27->Edit7->Text;
replot();
}
//---------------------------------------------------------------------------

void __fastcall TForm27::Button1Click(TObject *Sender)
{
void calcbo();
void replot();
double Ne(float,float,float);
   float tmin=atof(OKBottomDlg->Edit20->Text.c_str());
  float tmax=atof(OKBottomDlg->Edit21->Text.c_str());
float oldtemp,newtemp;
float contr,Neold;

do {
     do   {
      replot();            Form27->Refresh();
        calcbo();

        oldtemp=atof((Form27->Edit7->Text).c_str());
        float j=0;
        float tmed=0;
        for (int i=1;i< Form27->StringGrid2->RowCount;i++)
        {
        float ff=atof((Form27->StringGrid2->Cells[3][i]).c_str());
        if ((ff<= tmin | ff >= tmax) & ff !=0) Form27->StringGrid2->Cells[0][i]="X" ;
        if (Form27->StringGrid2->Cells[0][i]=="" & ff !=0)
        {
        tmed+=ff;
        j++;
        }
        }

        newtemp=tmed/j;


        if (newtemp <=0)
        {
        ShowMessage("At least one element must be selected");
        return;
        }
        Form27->Edit7->Text=FormatFloat("#0.0000",newtemp);


        }
        while((fabs(oldtemp-newtemp)/(newtemp)) > 0.01);

      
        float Neold=atof(Form27->Edit8->Text.c_str());

        if (Form27->RadioGroup1->ItemIndex==0)  {
                                                if(Form27->Edit2->Text==""){
                                                MessageDlg("The hydrogen width is undetermined. Please fit the H line.", mtWarning, TMsgDlgButtons()<<mbOK,0);
                                                break;
                                                                        }

        Form27->Edit8->Text=FormatFloat("0.00E+00",Ne(Neold,11600*newtemp,atof(Form16->Edit3->Text.c_str())));


                                                } else {
                                                        
                                                        return;
                                                        }

       contr=fabs(atof(Form27->Edit8->Text.c_str())-Neold)/Neold;
    } while (contr > 0.01);


}
//---------------------------------------------------------------------------
void replot()
{
void showsahaboltz();
while (Form27->Chart1->SeriesCount()>0)
                {
                Form27->Chart1->Series[0]->Free();
                }

                 for (int w=1; w<=Form27->StringGrid2->RowCount;w++)
                {
                Form27->StringGrid2->Cells[1][w]="";
                Form27->StringGrid2->Cells[2][w]="";
                Form27->StringGrid2->Cells[3][w]="";
                }


showsahaboltz();
}
//---------------------------------------------------------------------------
void calcbo()
{
void fit(float x[], float y[], int ndata, float sig[], int mwt, float *a, float *b, float *siga, float *sigb, float *chi2, float *q);

   int sc=Form27->Chart1->SeriesCount();
 for (int ii=0;ii < sc;ii++)
   {
        int reco= Form27->Chart1->Series[ii]->LastValueIndex;
        // Fit lineare (II versione)
        float ktt=1;
        float kt,q,qq,siga,erore,chi2,r;
        if (reco > 1)
                {
                // Costruisco i vettori

                float x[900],y[900],sig[900];
                int j;

                for (j=0;j < reco;j++)
                        {
                                float xx= Form27->Chart1->Series[ii]->XValues->Value[j];
                                float yy= Form27->Chart1->Series[ii]->YValues->Value[j];
                                x[j]=xx;
                                y[j]=yy;
                                sig[j]=1;

                        }

                // fine

                        int mwt=1;

                        fit(x, y, reco-1, sig, mwt, &qq, &ktt, &siga, &erore, &chi2, &r);

                        char tmd[20];
                         q=qq;
                         sprintf(tmd,"%1.4f",q);
                         Form27->StringGrid2->Cells[2][ii+1]=tmd;
                        if (ktt !=0)
                        {
                        sprintf(tmd,"%1.4f",-1.0/ktt);
                        Form27->StringGrid2->Cells[3][ii+1]=tmd;
                         }
                         else  Form27->StringGrid2->Cells[3][ii+1]="0";

                        float de=0;


        TLineSeries *MyLinSeries = new TLineSeries(Form27);
        MyLinSeries->ParentChart=Form27->Chart1;

         AnsiString spe=Form27->StringGrid2->Cells[1][ii+1];
         AnsiString s = "";
         s.cat_sprintf("Fit%s", spe);
        MyLinSeries->Name=s;
        double E1=Form27->Chart1->BottomAxis->Minimum;
        double E2=Form27->Chart1->BottomAxis->Maximum;
        double y1=qq+E1*ktt;
        double y2=qq+E2*ktt;
        MyLinSeries->SeriesColor=Form27->Chart1->Series[ii]->SeriesColor;
         if ((-1/ktt > atof(OKBottomDlg->Edit20->Text.c_str())) & (-1/ktt < atof(OKBottomDlg->Edit21->Text.c_str())))
        {
        MyLinSeries->AddXY(E1,y1,' ');
        MyLinSeries->AddXY(E2,y2,' ');
         }
        }
        }
 }
//---------------------------------------------------------------------------

void __fastcall TForm27::StringGrid2SelectCell(TObject *Sender, int ACol,
      int ARow, bool &CanSelect)
{
void showsahaboltz();
if (StringGrid2->Cells[0][ARow]=="")
{
StringGrid2->Cells[0][ARow]="X";
}
else
{
StringGrid2->Cells[0][ARow]="";
}
showsahaboltz();
}
//---------------------------------------------------------------------------

void __fastcall TForm27::Edit7Change(TObject *Sender)
{
/* void showsahaboltz();
showsahaboltz();
Form9->Edit1->Text=Form27->Edit7->Text;
Form9->RadioGroup1->ItemIndex=2;
*/
}
//---------------------------------------------------------------------------

void __fastcall TForm27::Edit8Change(TObject *Sender)
{
if (atof(Form27->Edit8->Text.c_str())==0) return;
void showsahaboltz();
showsahaboltz();
}
//---------------------------------------------------------------------------

void __fastcall TForm27::Chart1MouseMove(TObject *Sender,
      TShiftState Shift, int X, int Y)
{
float fattx,fatty,xx,yy,capx,capy;
if ((Chart1->ChartWidth == 0) || (Chart1->ChartHeight == 0))
{
Label3->Caption="00.00";
Label4->Caption="00.00";
}
else
{
xx=X;
yy=Y;
fattx=((xx-Chart1->ChartRect.Left)/(Chart1->ChartWidth));
fatty=((yy-Chart1->ChartRect.Bottom)/(Chart1->ChartHeight));
capx=Chart1->BottomAxis->Minimum+fattx*(Chart1->BottomAxis->Maximum-Chart1->BottomAxis->Minimum);
capy=Chart1->LeftAxis->Minimum-fatty*(Chart1->LeftAxis->Maximum-Chart1->LeftAxis->Minimum);
Label3->Caption=FormatFloat("#00.00",capx);
Label4->Caption=FormatFloat("#00.00",capy);
}
}
//---------------------------------------------------------------------------


void __fastcall TForm27::Copy1Click(TObject *Sender)
{
Graphics::TBitmap *FormImage;
TClipboard *MyClip;

MyClip = new TClipboard();

FormImage = GetFormImage();
MyClip->Assign(FormImage);          
}
//---------------------------------------------------------------------------

void __fastcall TForm27::SaveData1Click(TObject *Sender)
{
Form9->SaveDialog1->Title="Save Data";
Form9->SaveDialog1->Filter="Data|*.BLZ";
Form9->SaveDialog1->FileName = "*.BLZ";
Form9->SaveDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Reports";
char stringa[80]="The file already exists. Overwrite?";
if (Form9->SaveDialog1->Execute())
        {
        if (FileExists(Form9->SaveDialog1->FileName))
                {
                if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
 			mbCancel, 0) != IDYES)
          	return;
        }

FILE *out;
out = fopen(Form9->SaveDialog1->FileName.c_str(), "w");

 for (int ii=0;ii < Form27->Chart1->SeriesCount();ii++)
   {
          AnsiString ele=Form27->StringGrid2->Cells[1][ii+1];
                for (int j=0;j < Form27->Chart1->Series[ii]->LastValueIndex;j++)
                        {
                                float xx= Form27->Chart1->Series[ii]->XValues->Value[j];
                                float yy= Form27->Chart1->Series[ii]->YValues->Value[j];
                                fprintf(out,"%s %4.2f %4.2f\n",ele,xx,yy);
                        }
                // fine
 }
  fclose(out);
 }
}
//---------------------------------------------------------------------------

void __fastcall TForm27::ChangeBackground1Click(TObject *Sender)
{
int colore;
     SDIAppForm->ColorDialog1->Color=Form27->Chart1->BackColor;
    if (SDIAppForm->ColorDialog1->Execute())
    colore = SDIAppForm->ColorDialog1->Color;
    Form27->Chart1->BackColor=colore;
    return;
}
//---------------------------------------------------------------------------

void __fastcall TForm27::GridXOnOff1Click(TObject *Sender)
{
  if (Form27->Chart1->BottomAxis->Grid->Visible==false)  Form27->Chart1->BottomAxis->Grid->Visible=true;
   else
   Form27->Chart1->BottomAxis->Grid->Visible=false;
}
//---------------------------------------------------------------------------

void __fastcall TForm27::GridYOnOff1Click(TObject *Sender)
{
  if (Form27->Chart1->LeftAxis->Grid->Visible==false)  Form27->Chart1->LeftAxis->Grid->Visible=true;
   else
   Form27->Chart1->LeftAxis->Grid->Visible=false;
}
//---------------------------------------------------------------------------

void __fastcall TForm27::AnimatedZoomOnOff1Click(TObject *Sender)
{
 if (Form27->Chart1->AnimatedZoom==false) Form27->Chart1->AnimatedZoom=true;
   else
   Form27->Chart1->AnimatedZoom=false;
}
//---------------------------------------------------------------------------


void __fastcall TForm27::Button3Click(TObject *Sender)
{
replot();
}
//---------------------------------------------------------------------------




void __fastcall TForm27::Change(TObject *Sender)
{
if (Form27->RadioGroup1->ItemIndex==0) {
                                        Form27->Label5->Visible=true;
                                        Form27->Label6->Visible=true;
                                        Form27->Edit2->Visible=true;
                                        }
else    {
        Form27->Label5->Visible=false;
        Form27->Label6->Visible=false;
        Form27->Edit2->Visible=false;
        }


}
//---------------------------------------------------------------------------

